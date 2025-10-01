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
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from pyrogram import filters
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

from .bot_config import BotConfig
from .xiaozhi_client import XiaozhiClient, create_xiaozhi_client
from .core import Client, get_proxy

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
        
        # Runtime state
        self._running = False
        self._last_send_time = 0
        self._message_handlers = []
    
    def _create_client(
        self, account: str, proxy: str, session_dir: str,
        session_string: str, in_memory: bool
    ) -> Client:
        """Create Telegram client (reusing tg-signer infrastructure)"""
        api_id = os.getenv("TG_API_ID")
        api_hash = os.getenv("TG_API_HASH")
        
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
        
        # Initialize daily tasks if enabled
        if self.config.daily.enable_sign_in:
            await self._schedule_daily_signin()
    
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
            # Check for Xiaozhi AI triggers
            if self.xiaozhi_client and message.text:
                await self._handle_xiaozhi_message(message)
            
            # Check for custom rules
            await self._handle_custom_rules(message)
            
            # Parse response for state updates
            await self._parse_response(message)
            
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
    
    async def _parse_response(self, message: Message):
        """Parse bot responses for state updates"""
        # This would parse messages for completion of tasks
        # e.g., "点卯成功", "传功完成", etc.
        pass
    
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
            await self.client.send_message(self.config.chat_id, command)
            self._last_send_time = time.time()
            logger.info(f"Sent command: {command}")
        except Exception as e:
            logger.error(f"Failed to send command '{command}': {e}")
    
    async def _schedule_daily_signin(self):
        """Schedule daily sign-in task"""
        # Check state
        state = self.state_store.load("daily_state.json")
        key = f"acct_{self.account}_chat_{self.config.chat_id}"
        
        today = datetime.now().date().isoformat()
        daily_state = state.get(key, {})
        
        if daily_state.get("last_signin_date") == today:
            logger.info("Daily sign-in already completed today")
            return
        
        # Schedule sign-in command
        await self.command_queue.enqueue(
            ".点卯",
            priority=1,
            dedupe_key=f"daily:signin:{self.config.chat_id}"
        )
    
    async def _daily_reset_task(self):
        """Reset daily state at midnight"""
        while self._running:
            now = datetime.now()
            # Calculate time until next midnight
            tomorrow = now.date() + timedelta(days=1)
            midnight = datetime.combine(tomorrow, datetime.min.time())
            seconds_until_midnight = (midnight - now).total_seconds()
            
            await asyncio.sleep(seconds_until_midnight)
            
            # Reset daily state
            state = self.state_store.load("daily_state.json")
            key = f"acct_{self.account}_chat_{self.config.chat_id}"
            if key in state:
                state[key] = {}
                self.state_store.save("daily_state.json", state)
            
            logger.info("Daily state reset at midnight")
            
            # Re-schedule daily tasks
            if self.config.daily.enable_sign_in:
                await self._schedule_daily_signin()
    
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
