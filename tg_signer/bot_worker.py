"""
Channel Automation Bot Worker
Implements the main bot logic following ARCHITECTURE.md
"""
import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from pyrogram import filters
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

from .activity_manager import ActivityManager
from .bot_config import BotConfig
from .core import Client, get_proxy
from .daily_routine import DailyRoutine
from .herb_garden import HerbGarden
from .periodic_tasks import PeriodicTasks
from .star_observation import StarObservation
from .xiaozhi_client import XiaozhiClient, create_xiaozhi_client

logger = logging.getLogger("tg-signer.bot")


class StateStore:
    """Atomic state file management"""

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def load(self, filename: str) -> Dict[str, Any]:
        """Load state from file"""
        filepath = self.base_dir / filename
        if not filepath.exists():
            return {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load state from {filename}: {e}")
            return {}

    def save(self, filename: str, data: Dict[str, Any]):
        """Save state to file atomically"""
        filepath = self.base_dir / filename
        temp_filepath = filepath.with_suffix('.tmp')
        try:
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            temp_filepath.replace(filepath)
        except Exception as e:
            logger.error(f"Failed to save state to {filename}: {e}")
            if temp_filepath.exists():
                temp_filepath.unlink()


class CommandQueue:
    """
    Priority queue for command scheduling with deduplication and state tracking.
    
    Features:
    - Priority-based scheduling (P0=immediate, P1=high, P2=normal, P3=low)
    - Deduplication by key
    - Command state tracking (pending/executing/completed/failed)
    - Callback support for command completion
    """

    def __init__(self):
        self._queue = asyncio.PriorityQueue()
        self._pending = set()  # Deduplication keys
        self._order = 0
        self._command_states = {}  # Track command execution state
        self._callbacks = {}  # Command callbacks: dedupe_key -> callback_fn

    async def enqueue(
        self, 
        command: str, 
        when: float = None, 
        priority: int = 2, 
        dedupe_key: str = None,
        callback=None
    ):
        """
        Enqueue a command.

        Args:
            command: Command string to send
            when: Unix timestamp when to execute (None = now)
            priority: Priority level (0=immediate, 1=high, 2=normal, 3=low)
            dedupe_key: Key for deduplication (None = no dedup)
            callback: Optional async callback function to call after execution
        """
        when = when or time.time()

        if dedupe_key and dedupe_key in self._pending:
            logger.debug(f"[队列] 指令已去重: {command} (key={dedupe_key})")
            return False

        self._order += 1
        item = (when, priority, self._order, command, dedupe_key, callback)
        await self._queue.put(item)

        if dedupe_key:
            self._pending.add(dedupe_key)
            self._command_states[dedupe_key] = "pending"
            if callback:
                self._callbacks[dedupe_key] = callback

        # Calculate delay for logging
        delay = when - time.time()
        if delay > 1:
            logger.info(f"[队列] 加入指令: {command} (优先级=P{priority}, 延迟={delay:.1f}秒, key={dedupe_key})")
        else:
            logger.info(f"[队列] 加入指令: {command} (优先级=P{priority}, 立即执行, key={dedupe_key})")
        return True

    async def dequeue(self) -> tuple[str, Optional[str], Optional[callable]]:
        """
        Dequeue next command (blocks until available).
        
        Returns:
            (command, dedupe_key, callback)
        """
        when, priority, order, command, dedupe_key, callback = await self._queue.get()

        # Wait until scheduled time
        now = time.time()
        if when > now:
            wait_time = when - now
            logger.debug(f"[队列] 等待 {wait_time:.1f}秒后执行: {command}")
            await asyncio.sleep(wait_time)

        if dedupe_key:
            self._command_states[dedupe_key] = "executing"
        
        logger.info(f"[队列] 取出指令: {command} (优先级=P{priority})")
        return command, dedupe_key, callback

    def mark_completed(self, dedupe_key: str, success: bool = True):
        """Mark a command as completed or failed"""
        if dedupe_key:
            self._pending.discard(dedupe_key)
            self._command_states[dedupe_key] = "completed" if success else "failed"
            # Clean up callback after execution
            if dedupe_key in self._callbacks:
                del self._callbacks[dedupe_key]

    def get_state(self, dedupe_key: str) -> Optional[str]:
        """Get the state of a command by its dedupe key"""
        return self._command_states.get(dedupe_key)

    def empty(self) -> bool:
        """Check if queue is empty"""
        return self._queue.empty()
    
    def pending_count(self) -> int:
        """Get count of pending commands"""
        return len(self._pending)


class ChannelBot:
    """
    Channel automation bot worker.
    Manages automated interactions with a Telegram channel.
    """

    def __init__(
        self,
        config: BotConfig,
        account: str = "my_account",
        proxy: str = None,
        session_dir: str = ".",
        workdir: str = ".bot",
        session_string: str = None,
        in_memory: bool = False,
        xiaozhi_config_path: str = "config.json"
    ):
        self.config = config
        self.account = account
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)

        # Initialize state store
        self.state_store = StateStore(str(self.workdir / "states"))

        # Initialize command queue
        self.command_queue = CommandQueue()

        # Initialize Telegram client
        self.client = self._create_client(
            account, proxy, session_dir, session_string, in_memory
        )

        # Initialize Xiaozhi AI client
        self.xiaozhi_client = None
        if config.xiaozhi_ai.authorized_users:
            self.xiaozhi_client = self._load_xiaozhi_client(xiaozhi_config_path)

        # Initialize Daily Routine (每日例行)
        self.daily_routine = DailyRoutine(
            config, self.state_store, self.command_queue, config.chat_id, account
        )

        # Initialize Periodic Tasks (周期任务)
        self.periodic_tasks = PeriodicTasks(
            config, self.state_store, self.command_queue, config.chat_id, account
        )

        # Initialize Herb Garden (小药园)
        self.herb_garden = HerbGarden(
            config, self.state_store, self.command_queue, config.chat_id, account
        )

        # Initialize Star Observation (观星台)
        self.star_observation = StarObservation(
            config, self.state_store, self.command_queue, config.chat_id, account
        )

        # Initialize Activity Manager (活动管理器)
        self.activity_manager = ActivityManager(
            config.chat_id, account, self.xiaozhi_client
        )

        # Runtime state
        self._running = False
        self._last_send_time = 0
        self._message_handlers = []
        
        # Background task references
        self._command_processor_task = None
        self._daily_reset_task = None

    def _create_client(
        self, account: str, proxy: str, session_dir: str,
        session_string: str, in_memory: bool
    ) -> Client:
        """Create Telegram client (reusing tg-signer infrastructure)"""
        api_id = int(os.environ.get("TG_API_ID", 611335))
        api_hash = os.environ.get("TG_API_HASH", "d524b414d21f4d37f08684c1df41ac9c")

        if not api_id or not api_hash:
            raise ValueError("TG_API_ID and TG_API_HASH must be set")

        return Client(
            name=account,
            api_id=int(api_id),
            api_hash=api_hash,
            proxy=get_proxy(proxy),
            workdir=session_dir,
            session_string=session_string,
            in_memory=in_memory
        )

    def _load_xiaozhi_client(self, config_path: str) -> Optional[XiaozhiClient]:
        """Load Xiaozhi AI client from config"""
        if not Path(config_path).exists():
            logger.warning(f"Xiaozhi config not found: {config_path}")
            return None

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                xiaozhi_config = json.load(f)
            return create_xiaozhi_client(xiaozhi_config)
        except Exception as e:
            logger.error(f"Failed to load Xiaozhi client: {e}")
            return None

    async def start(self):
        """Start the bot"""
        self._running = True

        # Start Xiaozhi client if configured
        if self.xiaozhi_client:
            try:
                await self.xiaozhi_client.start()
                logger.info("Xiaozhi AI client started")
            except Exception as e:
                logger.error(f"Failed to start Xiaozhi client: {e}")

        # Start Telegram client
        await self.client.start()
        logger.info(f"Bot started for chat {self.config.chat_id}")

        # Register message handlers
        self._register_handlers()

        # Start background tasks - store references to track them
        self._command_processor_task = asyncio.create_task(self._command_processor_loop())
        self._daily_reset_task = asyncio.create_task(self._daily_reset_loop())
        logger.info("[核心] 后台任务已启动: 指令处理器、每日重置")

        # Start all modules with staggered delays to avoid slowmode
        # Each module will enqueue commands with internal delays,
        # but we also stagger module initialization to spread out enqueuing
        module_delay = 0
        
        # Daily tasks first (highest priority)
        logger.info("[核心] 启动每日任务模块...")
        await self.daily_routine.start()
        module_delay += 5  # Give daily tasks time to enqueue
        
        # Periodic tasks next
        await asyncio.sleep(module_delay)
        logger.info("[核心] 启动周期任务模块...")
        await self.periodic_tasks.start()
        module_delay = 5
        
        # Herb garden
        await asyncio.sleep(module_delay)
        logger.info("[核心] 启动小药园模块...")
        await self.herb_garden.start()
        module_delay = 5
        
        # Star observation last
        await asyncio.sleep(module_delay)
        logger.info("[核心] 启动观星台模块...")
        await self.star_observation.start()
        
        logger.info("[核心] 所有模块启动完成")

    async def stop(self):
        """Stop the bot"""
        logger.info("[核心] 正在停止机器人...")
        self._running = False

        # Cancel background tasks
        if self._command_processor_task:
            self._command_processor_task.cancel()
            try:
                await self._command_processor_task
            except asyncio.CancelledError:
                pass
        
        if self._daily_reset_task:
            self._daily_reset_task.cancel()
            try:
                await self._daily_reset_task
            except asyncio.CancelledError:
                pass

        if self.xiaozhi_client:
            await self.xiaozhi_client.stop()

        await self.client.stop()
        logger.info("[核心] 机器人已停止")

    def _register_handlers(self):
        """Register message handlers"""
        # Handle all messages from the configured chat
        handler = MessageHandler(
            self._on_message,
            filters.chat(self.config.chat_id)
        )
        self.client.add_handler(handler)
        self._message_handlers.append(handler)

    async def _on_message(self, client: Client, message: Message):
        """Handle incoming messages"""
        try:
            # Filter messages based on sender type
            # We want to process:
            # 1. Messages from bots (for command responses from channel bot)
            # 2. Messages that mention us (for activities/interactions)
            # Skip regular user messages that don't mention us
            
            should_process = False
            
            if message.from_user:
                is_bot = getattr(message.from_user, 'is_bot', False)
                if is_bot:
                    # Process all bot messages (command responses)
                    should_process = True
                else:
                    # For non-bot messages, check if it mentions us
                    has_mention = False
                    if message.entities:
                        for entity in message.entities:
                            entity_type = getattr(entity.type, 'name', str(entity.type))
                            if entity_type in ("MENTION", "TEXT_MENTION"):
                                has_mention = True
                                break
                    
                    if has_mention:
                        should_process = True
            else:
                # Messages without from_user (channel posts) - process them
                should_process = True
            
            if not should_process:
                logger.debug(f"[消息] 跳过非相关消息")
                return
            
            # Log incoming message for debugging
            msg_preview = message.text[:50] if message.text else "(无文本)"
            logger.debug(f"[消息] 收到: {msg_preview}...")
            
            handled = False

            # Check modules in order (following ARCHITECTURE.md pipeline)
            # Daily -> Periodic -> Star -> Herb -> YuanYing -> Activity -> AI

            # 1. Daily Routine
            if await self.daily_routine.handle_message(message):
                handled = True
                logger.debug("[消息] 由每日任务模块处理")

            # 2. Periodic Tasks (闭关、引道、启阵、问道、裂缝)
            if not handled and await self.periodic_tasks.handle_message(message):
                handled = True
                logger.debug("[消息] 由周期任务模块处理")

            # 3. Star Observation (观星台)
            if not handled and await self.star_observation.handle_message(message):
                handled = True
                logger.debug("[消息] 由观星台模块处理")

            # 4. Herb Garden (小药园)
            if not handled and await self.herb_garden.handle_message(message):
                handled = True
                logger.debug("[消息] 由小药园模块处理")

            # 5. Check Activity Manager for activity matching
            if not handled and message.text and self.config.activity.enabled:
                activity_match = self.activity_manager.match_activity(
                    message.text,
                    message,
                    enable_ai=bool(self.xiaozhi_client and self.config.xiaozhi_ai.authorized_users)
                )
                if activity_match:
                    response_command, response_type, priority = activity_match
                    logger.info(f"[活动] 匹配成功，响应: {response_command} (优先级=P{priority})")

                    # Time-sensitive activities use priority=0 for immediate/high-priority execution
                    # This ensures they are processed before other queued commands
                    await self.command_queue.enqueue(
                        response_command,
                        priority=priority,  # 0=immediate, 1=high, 2=normal, 3=low
                        dedupe_key=f"activity:{response_command}:{self.config.chat_id}"
                    )
                    handled = True

            # 6. Check for Xiaozhi AI triggers (if not handled by activity)
            if not handled and self.xiaozhi_client and message.text:
                await self._handle_xiaozhi_message(message)

            # 7. Check for custom rules (if not handled)
            if not handled:
                await self._handle_custom_rules(message)
            
            if not handled:
                logger.debug(f"[消息] 未被任何模块处理")

        except Exception as e:
            logger.error(f"[消息] 处理错误: {e}", exc_info=True)

    async def _handle_xiaozhi_message(self, message: Message):
        """Handle messages that might trigger Xiaozhi AI"""
        if not message.text:
            return

        # Check if user is authorized
        if message.from_user.id not in self.config.xiaozhi_ai.authorized_users:
            return

        # Check if user is blacklisted
        if message.from_user.id in self.config.xiaozhi_ai.blacklist_users:
            return

        # Check for trigger keywords
        text = message.text
        triggered = False
        for keyword in self.config.xiaozhi_ai.trigger_keywords:
            if keyword in text:
                triggered = True
                # Remove trigger keyword from text
                text = text.replace(keyword, "").strip()
                break

        if not triggered:
            return

        # Check for filter keywords
        for keyword in self.config.xiaozhi_ai.filter_keywords:
            if keyword in text:
                logger.info(f"Message filtered due to keyword: {keyword}")
                return

        # Send to Xiaozhi AI and enqueue response
        try:
            response = await self.xiaozhi_client.send_message(text)
            reply_text = f"{self.config.xiaozhi_ai.response_prefix}{response}"
            
            # Enqueue the AI response instead of directly replying
            # This ensures rate limiting and proper sequencing
            await self.command_queue.enqueue(
                reply_text,
                priority=2,  # Normal priority for AI responses
                dedupe_key=f"ai_reply:{message.from_user.id}:{time.time()}"
            )
            logger.info(f"Xiaozhi AI response queued for user {message.from_user.id}")
        except Exception as e:
            logger.error(f"Failed to get Xiaozhi AI response: {e}")

    async def _handle_custom_rules(self, message: Message):
        """Handle custom command-response rules"""
        if not message.text:
            return

        for rule in self.config.custom_rules:
            if not rule.enabled:
                continue

            if re.search(rule.pattern, message.text):
                logger.info(f"Custom rule matched: {rule.pattern}")

                # Check cooldown
                state_key = f"rule_cooldown_{rule.pattern}"
                state = self.state_store.load("custom_rules.json")
                last_triggered = state.get(state_key, 0)

                if time.time() - last_triggered < rule.cooldown_seconds:
                    logger.debug(f"Rule in cooldown: {rule.pattern}")
                    continue

                # Enqueue response instead of directly replying
                if rule.response:
                    await self.command_queue.enqueue(
                        rule.response,
                        priority=2,  # Normal priority for custom rules
                        dedupe_key=f"custom_rule:{rule.pattern}:{time.time()}"
                    )

                if rule.action:
                    # Execute action (would need to be implemented)
                    logger.info(f"Executing action: {rule.action}")

                # Update cooldown
                state[state_key] = time.time()
                self.state_store.save("custom_rules.json", state)


    async def _command_processor_loop(self):
        """
        Background task to process command queue serially.
        
        This ensures all commands are executed in order with proper:
        - Rate limiting between commands
        - State tracking (pending -> executing -> completed/failed)
        - Callback execution after command completion
        """
        logger.info("[队列] 指令处理器已启动")
        while self._running:
            try:
                if not self.command_queue.empty():
                    command, dedupe_key, callback = await self.command_queue.dequeue()
                    logger.info(f"[队列] 开始执行: {command}")
                    success = await self._send_command(command, dedupe_key)
                    
                    # Mark command as completed/failed
                    if dedupe_key:
                        self.command_queue.mark_completed(dedupe_key, success)
                        if success:
                            logger.debug(f"[队列] 指令完成: {command}")
                        else:
                            logger.warning(f"[队列] 指令失败: {command}")
                    
                    # Execute callback if provided
                    if callback and success:
                        try:
                            logger.debug(f"[队列] 执行回调: {command}")
                            if asyncio.iscoroutinefunction(callback):
                                await callback()
                            else:
                                callback()
                        except Exception as e:
                            logger.error(f"[队列] 回调失败 '{command}': {e}", exc_info=True)
                else:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"[队列] 处理器错误: {e}", exc_info=True)
        
        logger.info("[队列] 指令处理器已停止")

    async def _send_command(self, command: str, dedupe_key: str = None) -> bool:
        """
        Send a command with rate limiting and error handling.
        
        Args:
            command: Command string to send
            dedupe_key: Deduplication key for state tracking
            
        Returns:
            True if command sent successfully, False otherwise
        """
        # Rate limiting - ensure minimum interval between sends
        now = time.time()
        elapsed = now - self._last_send_time
        if elapsed < self.config.min_send_interval:
            wait_time = self.config.min_send_interval - elapsed
            logger.debug(f"[发送] 速率限制，等待{wait_time:.1f}秒")
            await asyncio.sleep(wait_time)

        try:
            # Check if transmission needs reply_to
            reply_to_message_id = None
            if "宗门传功" in command and self.daily_routine.state.last_message_id:
                reply_to_message_id = self.daily_routine.state.last_message_id
                logger.debug(f"[发送] 传功需要回复消息ID: {reply_to_message_id}")

            logger.info(f"[发送] 正在发送: {command}")
            message = await self.client.send_message(
                self.config.chat_id,
                command,
                reply_to_message_id=reply_to_message_id
            )
            self._last_send_time = time.time()

            # Track message ID for future replies (especially for transmission)
            if message and message.id:
                self.daily_routine.update_last_message_id(message.id)
                logger.debug(f"[发送] 消息ID: {message.id}")

            logger.info(f"[发送] ✓ 发送成功: {command}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            
            # Handle slowmode errors specially
            if "SLOWMODE_WAIT" in error_msg:
                import re
                wait_match = re.search(r'wait (\d+) seconds', error_msg)
                if wait_match:
                    wait_seconds = int(wait_match.group(1))
                    logger.warning(f"[发送] ✗ 慢速模式限制，需等待{wait_seconds}秒: {command}")
                    # Re-enqueue the command after the wait time
                    await self.command_queue.enqueue(
                        command,
                        when=time.time() + wait_seconds + 1,
                        priority=0,  # High priority for retry
                        dedupe_key=f"{dedupe_key}_retry" if dedupe_key else None
                    )
                    return False
                else:
                    logger.warning(f"[发送] ✗ 慢速模式限制: {command}")
            else:
                logger.error(f"[发送] ✗ 发送失败 '{command}': {error_msg}")
            
            return False

    async def _daily_reset_loop(self):
        """Reset daily state at midnight"""
        logger.info("[核心] 每日重置任务已启动")
        while self._running:
            now = datetime.now()
            # Calculate time until next midnight
            tomorrow = now.date() + timedelta(days=1)
            midnight = datetime.combine(tomorrow, datetime.min.time())
            seconds_until_midnight = (midnight - now).total_seconds()

            logger.debug(f"[核心] 下次重置时间: {midnight} (距离 {seconds_until_midnight:.0f}秒)")
            await asyncio.sleep(seconds_until_midnight)

            # Reset daily state for all modules
            logger.info("[核心] 午夜重置每日任务状态")

            # Reset daily routine
            self.daily_routine.reset_daily()

            # Re-schedule daily tasks
            await self.daily_routine.start()
        
        logger.info("[核心] 每日重置任务已停止")

    async def run(self):
        """Run the bot (blocking)"""
        await self.start()

        try:
            # Keep running until stopped
            while self._running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            await self.stop()
