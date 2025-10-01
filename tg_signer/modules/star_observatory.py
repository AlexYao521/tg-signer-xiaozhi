"""
Star Observatory Automation Module (观星台自动化)
Based on ARCHITECTURE.md section 4.5
"""
import asyncio
import logging
import re
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger("tg-signer.star_observatory")


class StarObservatoryModule:
    """
    Star Observatory Automation Module
    
    Handles:
    - Observation (`.观星台`)
    - Star pulling (`.牵引星辰 <星名>`)
    - Essence collection (`.收集精华`)
    - Star pacification (`.安抚星辰`)
    - Star sequence rotation
    - Cooldown management
    """
    
    def __init__(
        self,
        config,
        state_store,
        command_queue,
        chat_id: int,
        account: str
    ):
        self.config = config.star_observation
        self.state_store = state_store
        self.command_queue = command_queue
        self.chat_id = chat_id
        self.account = account
        
        # State key for this account/chat
        self.state_key = f"acct_{account}_chat_{chat_id}"
    
    async def start(self):
        """Start star observatory automation"""
        if not self.config.enabled:
            logger.info("Star observatory module disabled")
            return
        
        logger.info("Starting star observatory module")
        
        # Schedule initial observation
        await self._schedule_observation()
    
    async def _schedule_observation(self):
        """Schedule a star observatory observation"""
        await self.command_queue.enqueue(
            ".观星台",
            priority=3,
            dedupe_key=f"star:observe:{self.chat_id}"
        )
        logger.debug("Scheduled star observatory observation")
    
    async def handle_message(self, message) -> bool:
        """
        Handle incoming message from the channel.
        
        Returns:
            True if message was handled, False otherwise
        """
        if not message.text:
            return False
        
        text = message.text
        
        # Parse observation response
        if "观星台" in text or "星辰" in text:
            await self._parse_observation_response(text)
            return True
        
        # Parse action responses
        if any(keyword in text for keyword in ["牵引", "收集精华", "安抚"]):
            await self._parse_action_response(text)
            return True
        
        return False
    
    async def _parse_observation_response(self, text: str):
        """
        Parse star observatory observation response.
        
        Expected patterns:
        - "观星台空闲" -> pull star
        - "可以收集精华" -> collect essence
        - "星辰躁动" -> pacify star
        - "冷却中, 剩余时间: X分钟"
        """
        logger.debug(f"Parsing star observatory response: {text}")
        
        state = self.state_store.load("star_state.json")
        star_state = state.get(self.state_key, {})
        
        now = time.time()
        star_state["last_observe_ts"] = now
        
        # Check if can collect essence
        if "可以收集精华" in text or "精华已满" in text:
            logger.info("Star essence ready for collection")
            await self.command_queue.enqueue(
                ".收集精华",
                priority=2,
                dedupe_key=f"star:collect:{self.chat_id}"
            )
            
            # Schedule observation after collection
            await self.command_queue.enqueue(
                ".观星台",
                when=now + 5,
                priority=3,
                dedupe_key=f"star:observe:post_collect:{self.chat_id}"
            )
        
        # Check if star is agitated
        elif "星辰躁动" in text or "不稳定" in text:
            logger.info("Star is agitated, needs pacification")
            
            # Check pacification cooldown
            last_pacify = star_state.get("last_pacify_ts", 0)
            pacify_cooldown = 300  # 5 minutes default
            
            if now - last_pacify > pacify_cooldown:
                await self.command_queue.enqueue(
                    ".安抚星辰",
                    priority=2,
                    dedupe_key=f"star:pacify:{self.chat_id}"
                )
                star_state["last_pacify_ts"] = now
            else:
                logger.debug("Pacification in cooldown")
        
        # Check if observatory is idle (need to pull star)
        elif "观星台空闲" in text or "无星辰" in text:
            logger.info("Observatory is idle, pulling star")
            await self._schedule_star_pull()
        
        # Parse cooldown information
        cooldown_pattern = r"冷却中.*?[:：]\s*(\d+)\s*分钟"
        cooldown_match = re.search(cooldown_pattern, text)
        if cooldown_match:
            minutes_remaining = int(cooldown_match.group(1))
            logger.info(f"Observatory in cooldown for {minutes_remaining} minutes")
            
            # Schedule next observation based on cooldown
            next_observe_time = now + (minutes_remaining * 60) + 60  # Add 1 minute buffer
            star_state["next_observe_ts"] = next_observe_time
            
            await self.command_queue.enqueue(
                ".观星台",
                when=next_observe_time,
                priority=3,
                dedupe_key=f"star:observe:scheduled:{self.chat_id}"
            )
        else:
            # No cooldown info, schedule periodic observation
            next_observe_time = now + 600  # 10 minutes default
            star_state["next_observe_ts"] = next_observe_time
            
            await self.command_queue.enqueue(
                ".观星台",
                when=next_observe_time,
                priority=3,
                dedupe_key=f"star:observe:periodic:{self.chat_id}"
            )
        
        # Save state
        state[self.state_key] = star_state
        self.state_store.save("star_state.json", state)
    
    async def _schedule_star_pull(self):
        """Schedule star pulling action with sequence rotation"""
        state = self.state_store.load("star_state.json")
        star_state = state.get(self.state_key, {})
        
        # Get star from sequence
        sequence = self.config.sequence
        if not sequence:
            star_name = self.config.default_star
        else:
            sequence_index = star_state.get("sequence_index", 0)
            star_name = sequence[sequence_index % len(sequence)]
            
            # Update sequence index for next time
            star_state["sequence_index"] = (sequence_index + 1) % len(sequence)
        
        command = f".牵引星辰 {star_name}"
        await self.command_queue.enqueue(
            command,
            priority=2,
            dedupe_key=f"star:pull:{self.chat_id}"
        )
        
        logger.info(f"Scheduled star pull: {star_name}")
        
        # Save state
        state = self.state_store.load("star_state.json")
        state[self.state_key] = star_state
        self.state_store.save("star_state.json", state)
    
    async def _parse_action_response(self, text: str):
        """Parse response to star actions"""
        logger.debug(f"Parsing star action response: {text}")
        
        state = self.state_store.load("star_state.json")
        star_state = state.get(self.state_key, {})
        
        # Track success/failure
        if "成功" in text or "完成" in text:
            logger.info(f"Star action successful: {text[:50]}")
            
            # Update counters
            if "收集精华" in text:
                star_state["essence_collected"] = star_state.get("essence_collected", 0) + 1
            elif "牵引" in text:
                star_state["stars_pulled"] = star_state.get("stars_pulled", 0) + 1
            elif "安抚" in text:
                star_state["last_pacify_ts"] = time.time()
        
        elif "失败" in text or "错误" in text:
            logger.warning(f"Star action failed: {text[:50]}")
            
            # Handle specific failures
            if "材料不足" in text:
                logger.warning("Insufficient materials for star action")
        
        # Save state
        state[self.state_key] = star_state
        self.state_store.save("star_state.json", state)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current star observatory status"""
        state = self.state_store.load("star_state.json")
        star_state = state.get(self.state_key, {})
        
        return {
            "enabled": self.config.enabled,
            "last_observe": star_state.get("last_observe_ts"),
            "next_observe": star_state.get("next_observe_ts"),
            "sequence_index": star_state.get("sequence_index", 0),
            "essence_collected": star_state.get("essence_collected", 0),
            "stars_pulled": star_state.get("stars_pulled", 0),
            "default_star": self.config.default_star,
            "sequence": self.config.sequence
        }
