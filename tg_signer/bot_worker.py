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
    """Priority queue for command scheduling with deduplication"""

    def __init__(self):
        self._queue = asyncio.PriorityQueue()
        self._pending = set()  # Deduplication keys
        self._order = 0

    async def enqueue(self, command: str, when: float = None, priority: int = 5, dedupe_key: str = None):
        """
        Enqueue a command.

        Args:
            command: Command string to send
            when: Unix timestamp when to execute (None = now)
            priority: Priority level (lower = higher priority)
            dedupe_key: Key for deduplication (None = no dedup)
        """
        when = when or time.time()

        if dedupe_key and dedupe_key in self._pending:
            logger.debug(f"Command deduplicated: {dedupe_key}")
            return

        self._order += 1
        item = (when, priority, self._order, command, dedupe_key)
        await self._queue.put(item)

        if dedupe_key:
            self._pending.add(dedupe_key)

        logger.debug(f"Enqueued command: {command} (when={when}, priority={priority})")

    async def dequeue(self) -> tuple[str, Optional[str]]:
        """Dequeue next command (blocks until available)"""
        when, priority, order, command, dedupe_key = await self._queue.get()

        # Wait until scheduled time
        now = time.time()
        if when > now:
            await asyncio.sleep(when - now)

        if dedupe_key:
            self._pending.discard(dedupe_key)

        return command, dedupe_key

    def empty(self) -> bool:
        """Check if queue is empty"""
        return self._queue.empty()


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

        # Start background tasks
        asyncio.create_task(self._command_processor())
        asyncio.create_task(self._daily_reset_task())

        # Start all modules
        await self.daily_routine.start()
        await self.periodic_tasks.start()
        await self.herb_garden.start()
        await self.star_observation.start()

    async def stop(self):
        """Stop the bot"""
        self._running = False

        if self.xiaozhi_client:
            await self.xiaozhi_client.stop()

        await self.client.stop()
        logger.info("Bot stopped")

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
            handled = False

            # Check modules in order (following ARCHITECTURE.md pipeline)
            # Daily -> Periodic -> Star -> Herb -> YuanYing -> Activity -> AI

            # 1. Daily Routine
            if await self.daily_routine.handle_message(message):
                handled = True
                logger.debug("Message handled by Daily Routine")

            # 2. Periodic Tasks (闭关、引道、启阵、问道、裂缝)
            if not handled and await self.periodic_tasks.handle_message(message):
                handled = True
                logger.debug("Message handled by Periodic Tasks")

            # 3. Star Observation (观星台)
            if not handled and await self.star_observation.handle_message(message):
                handled = True
                logger.debug("Message handled by Star Observation")

            # 4. Herb Garden (小药园)
            if not handled and await self.herb_garden.handle_message(message):
                handled = True
                logger.debug("Message handled by Herb Garden")

            # 5. Check Activity Manager for activity matching
            if not handled and message.text and self.config.activity.enabled:
                activity_match = self.activity_manager.match_activity(
                    message.text,
                    message,
                    enable_ai=bool(self.xiaozhi_client and self.config.xiaozhi_ai.authorized_users)
                )
                if activity_match:
                    response_command, response_type, priority = activity_match
                    logger.info(f"Activity matched: {response_command}")

                    # Enqueue the response command/text
                    await self.command_queue.enqueue(
                        response_command,
                        priority=priority,
                        dedupe_key=f"activity:{response_command}:{self.config.chat_id}"
                    )
                    handled = True

            # 6. Check for Xiaozhi AI triggers (if not handled by activity)
            if not handled and self.xiaozhi_client and message.text:
                await self._handle_xiaozhi_message(message)

            # 7. Check for custom rules (if not handled)
            if not handled:
                await self._handle_custom_rules(message)

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

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

        # Send to Xiaozhi AI
        try:
            response = await self.xiaozhi_client.send_message(text)
            reply_text = f"{self.config.xiaozhi_ai.response_prefix}{response}"
            await message.reply(reply_text)
            logger.info(f"Xiaozhi AI replied to message from {message.from_user.id}")
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

                # Execute response
                if rule.response:
                    await message.reply(rule.response)

                if rule.action:
                    # Execute action (would need to be implemented)
                    logger.info(f"Executing action: {rule.action}")

                # Update cooldown
                state[state_key] = time.time()
                self.state_store.save("custom_rules.json", state)


    async def _command_processor(self):
        """Background task to process command queue"""
        while self._running:
            try:
                if not self.command_queue.empty():
                    command, dedupe_key = await self.command_queue.dequeue()
                    await self._send_command(command)
                else:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error in command processor: {e}", exc_info=True)

    async def _send_command(self, command: str):
        """Send a command with rate limiting"""
        # Rate limiting
        now = time.time()
        elapsed = now - self._last_send_time
        if elapsed < self.config.min_send_interval:
            await asyncio.sleep(self.config.min_send_interval - elapsed)

        try:
            # Check if transmission needs reply_to
            reply_to_message_id = None
            if "宗门传功" in command and self.daily_routine.state.last_message_id:
                reply_to_message_id = self.daily_routine.state.last_message_id
                logger.debug(f"Sending transmission with reply_to: {reply_to_message_id}")

            message = await self.client.send_message(
                self.config.chat_id,
                command,
                reply_to_message_id=reply_to_message_id
            )
            self._last_send_time = time.time()

            # Track message ID for future replies (especially for transmission)
            if message and message.id:
                self.daily_routine.update_last_message_id(message.id)

            logger.info(f"Sent command: {command}")
        except Exception as e:
            logger.error(f"Failed to send command '{command}': {e}")

    async def _daily_reset_task(self):
        """Reset daily state at midnight"""
        while self._running:
            now = datetime.now()
            # Calculate time until next midnight
            tomorrow = now.date() + timedelta(days=1)
            midnight = datetime.combine(tomorrow, datetime.min.time())
            seconds_until_midnight = (midnight - now).total_seconds()

            await asyncio.sleep(seconds_until_midnight)

            # Reset daily state for all modules
            logger.info("Daily state reset at midnight")

            # Reset daily routine
            self.daily_routine.reset_daily()

            # Re-schedule daily tasks
            await self.daily_routine.start()

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
