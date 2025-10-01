"""
Herb Garden Automation Module (小药园自动化)
Based on ARCHITECTURE.md section 4.16
"""
import asyncio
import logging
import re
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger("tg-signer.herb_garden")


class HerbGardenModule:
    """
    Herb Garden Automation Module
    
    Handles:
    - Scanning (`.小药园`)
    - Maintenance (除草/除虫/浇水)
    - Harvesting (采药)
    - Seeding (播种)
    - ETA-based scheduling
    """
    
    def __init__(
        self,
        config,
        state_store,
        command_queue,
        chat_id: int,
        account: str
    ):
        self.config = config.herb_garden
        self.state_store = state_store
        self.command_queue = command_queue
        self.chat_id = chat_id
        self.account = account
        
        # State key for this account/chat
        self.state_key = f"acct_{account}_chat_{chat_id}"
    
    async def start(self):
        """Start herb garden automation"""
        if not self.config.enabled:
            logger.info("Herb garden module disabled")
            return
        
        logger.info("Starting herb garden module")
        
        # Schedule initial scan
        await self._schedule_scan()
    
    async def _schedule_scan(self):
        """Schedule a herb garden scan"""
        await self.command_queue.enqueue(
            ".小药园",
            priority=3,
            dedupe_key=f"herb:scan:{self.chat_id}"
        )
        logger.debug("Scheduled herb garden scan")
    
    async def handle_message(self, message) -> bool:
        """
        Handle incoming message from the channel.
        
        Returns:
            True if message was handled, False otherwise
        """
        if not message.text:
            return False
        
        text = message.text
        
        # Parse scan response
        if "小药园" in text or "药园" in text:
            await self._parse_scan_response(text)
            return True
        
        # Parse maintenance responses
        if any(keyword in text for keyword in ["除草", "除虫", "浇水", "采药", "播种"]):
            await self._parse_action_response(text)
            return True
        
        return False
    
    async def _parse_scan_response(self, text: str):
        """
        Parse herb garden scan response.
        
        Expected patterns:
        - "药园状态: 需要除草"
        - "药园状态: 需要除虫"
        - "药园状态: 需要浇水"
        - "可以采药, 剩余时间: 2小时"
        - "药园空闲"
        """
        logger.debug(f"Parsing herb garden scan response: {text}")
        
        state = self.state_store.load("herb_garden_state.json")
        garden_state = state.get(self.state_key, {})
        
        now = time.time()
        garden_state["last_scan_ts"] = now
        
        # Check for maintenance needs
        needs_maintenance = []
        if "需要除草" in text or "杂草丛生" in text:
            needs_maintenance.append("除草")
        if "需要除虫" in text or "虫害" in text:
            needs_maintenance.append("除虫")
        if "需要浇水" in text or "干旱" in text:
            needs_maintenance.append("浇水")
        
        # Schedule maintenance if needed
        if needs_maintenance:
            logger.info(f"Herb garden needs maintenance: {needs_maintenance}")
            for action in needs_maintenance:
                await self.command_queue.enqueue(
                    f".{action}",
                    priority=2,
                    dedupe_key=f"herb:maintenance:{action}:{self.chat_id}"
                )
            
            # Schedule rescan after maintenance
            await self.command_queue.enqueue(
                ".小药园",
                when=now + self.config.post_maintenance_rescan,
                priority=3,
                dedupe_key=f"herb:scan:post_maintenance:{self.chat_id}"
            )
        
        # Check if ready for harvest
        if "可以采药" in text or "成熟" in text:
            logger.info("Herbs ready for harvest")
            await self.command_queue.enqueue(
                ".采药",
                priority=2,
                dedupe_key=f"herb:harvest:{self.chat_id}"
            )
            
            # Schedule rescan after harvest
            await self.command_queue.enqueue(
                ".小药园",
                when=now + self.config.post_harvest_rescan,
                priority=3,
                dedupe_key=f"herb:scan:post_harvest:{self.chat_id}"
            )
            
            garden_state["last_harvest_ts"] = now
        
        # Extract remaining time if available
        time_pattern = r"剩余时间[:：]\s*(\d+)\s*小时"
        time_match = re.search(time_pattern, text)
        if time_match:
            hours_remaining = int(time_match.group(1))
            logger.info(f"Herbs will be ready in {hours_remaining} hours")
            
            # Schedule next scan based on ETA
            next_scan_time = now + (hours_remaining * 3600) + 60  # Add 1 minute buffer
            garden_state["next_scan_ts"] = next_scan_time
            
            await self.command_queue.enqueue(
                ".小药园",
                when=next_scan_time,
                priority=3,
                dedupe_key=f"herb:scan:scheduled:{self.chat_id}"
            )
        else:
            # No time info, schedule periodic scan
            next_scan_time = now + self.config.scan_interval_min
            garden_state["next_scan_ts"] = next_scan_time
            
            await self.command_queue.enqueue(
                ".小药园",
                when=next_scan_time,
                priority=3,
                dedupe_key=f"herb:scan:periodic:{self.chat_id}"
            )
        
        # Check if garden is idle and needs seeding
        if "药园空闲" in text or "无药草" in text:
            logger.info("Herb garden is idle, attempting to seed")
            await self._schedule_seeding()
            garden_state["is_idle"] = True
        else:
            garden_state["is_idle"] = False
        
        # Save state
        state[self.state_key] = garden_state
        self.state_store.save("herb_garden_state.json", state)
    
    async def _parse_action_response(self, text: str):
        """Parse response to maintenance/harvest/seeding actions"""
        logger.debug(f"Parsing herb garden action response: {text}")
        
        state = self.state_store.load("herb_garden_state.json")
        garden_state = state.get(self.state_key, {})
        
        # Track success/failure
        if "成功" in text or "完成" in text:
            logger.info(f"Herb garden action successful: {text[:50]}")
            
            # Update last action time
            if "采药" in text:
                garden_state["last_harvest_ts"] = time.time()
            elif "播种" in text:
                garden_state["last_seed_ts"] = time.time()
                garden_state["is_idle"] = False
        
        elif "失败" in text or "错误" in text:
            logger.warning(f"Herb garden action failed: {text[:50]}")
            
            # Handle seed shortage
            if "种子不足" in text or "没有种子" in text:
                logger.warning("Seed shortage detected, attempting to exchange")
                await self._schedule_seed_exchange()
        
        # Save state
        state[self.state_key] = garden_state
        self.state_store.save("herb_garden_state.json", state)
    
    async def _schedule_seeding(self):
        """Schedule seeding action"""
        seed_name = self.config.default_seed
        command = f".播种 {seed_name}"
        
        await self.command_queue.enqueue(
            command,
            priority=2,
            dedupe_key=f"herb:seed:{self.chat_id}"
        )
        
        logger.info(f"Scheduled seeding: {seed_name}")
    
    async def _schedule_seed_exchange(self):
        """Schedule seed exchange if configured"""
        if not self.config.seeds:
            logger.warning("No seed exchange configuration available")
            return
        
        seed_name = self.config.default_seed
        seed_config = self.config.seeds.get(seed_name)
        
        if not seed_config:
            logger.warning(f"No configuration for seed: {seed_name}")
            return
        
        # Check if we've tried recently
        state = self.state_store.load("herb_garden_state.json")
        garden_state = state.get(self.state_key, {})
        last_exchange = garden_state.get("last_seed_exchange_ts", 0)
        
        if time.time() - last_exchange < self.config.seed_shortage_retry:
            logger.debug("Seed exchange attempted too recently, skipping")
            return
        
        # Schedule exchange command
        exchange_cmd = seed_config.exchange_command
        await self.command_queue.enqueue(
            exchange_cmd,
            priority=2,
            dedupe_key=f"herb:exchange:{self.chat_id}"
        )
        
        logger.info(f"Scheduled seed exchange: {exchange_cmd}")
        
        # Update state
        garden_state["last_seed_exchange_ts"] = time.time()
        state[self.state_key] = garden_state
        self.state_store.save("herb_garden_state.json", state)
        
        # Retry seeding after exchange
        await asyncio.sleep(5)  # Wait for exchange to complete
        await self._schedule_seeding()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current herb garden status"""
        state = self.state_store.load("herb_garden_state.json")
        garden_state = state.get(self.state_key, {})
        
        return {
            "enabled": self.config.enabled,
            "last_scan": garden_state.get("last_scan_ts"),
            "last_harvest": garden_state.get("last_harvest_ts"),
            "next_scan": garden_state.get("next_scan_ts"),
            "is_idle": garden_state.get("is_idle", False),
            "default_seed": self.config.default_seed
        }
