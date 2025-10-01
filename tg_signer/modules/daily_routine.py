"""
Daily Routine Module (每日例行任务)
Based on ARCHITECTURE.md section 4.3
"""
import logging
import time
from typing import Dict, Any
from datetime import datetime, date

logger = logging.getLogger("tg-signer.daily_routine")


class DailyRoutineModule:
    """
    Daily Routine Module
    
    Handles:
    - Sign-in (点卯)
    - Transmission (传功)
    - Greeting (问安)
    """
    
    def __init__(
        self,
        config,
        state_store,
        command_queue,
        chat_id: int,
        account: str
    ):
        self.config = config.daily
        self.state_store = state_store
        self.command_queue = command_queue
        self.chat_id = chat_id
        self.account = account
        
        # State key for this account/chat
        self.state_key = f"acct_{account}_chat_{chat_id}"
    
    async def start(self):
        """Start daily routine automation"""
        logger.info("Starting daily routine module")
        await self._schedule_daily_tasks()
    
    async def _schedule_daily_tasks(self):
        """Schedule daily tasks if not yet completed today"""
        state = self.state_store.load("daily_state.json")
        daily_state = state.get(self.state_key, {})
        
        today = date.today().isoformat()
        last_date = daily_state.get("last_date")
        
        # Reset if it's a new day
        if last_date != today:
            daily_state = {
                "last_date": today,
                "sign_in_done": False,
                "transmission_count": 0,
                "greeting_done": False
            }
        
        # Schedule sign-in
        if self.config.enable_sign_in and not daily_state.get("sign_in_done"):
            await self.command_queue.enqueue(
                ".点卯",
                priority=1,
                dedupe_key=f"daily:signin:{self.chat_id}"
            )
            logger.info("Scheduled daily sign-in")
        
        # Schedule transmission
        if self.config.enable_transmission and daily_state.get("transmission_count", 0) < 3:
            await self.command_queue.enqueue(
                ".传功",
                priority=1,
                dedupe_key=f"daily:transmission:{self.chat_id}"
            )
            logger.info("Scheduled daily transmission")
        
        # Schedule greeting
        if self.config.enable_greeting and not daily_state.get("greeting_done"):
            await self.command_queue.enqueue(
                ".问安",
                priority=1,
                dedupe_key=f"daily:greeting:{self.chat_id}"
            )
            logger.info("Scheduled daily greeting")
        
        # Save state
        state[self.state_key] = daily_state
        self.state_store.save("daily_state.json", state)
    
    async def handle_message(self, message) -> bool:
        """Handle incoming message and update state"""
        if not message.text:
            return False
        
        text = message.text
        state = self.state_store.load("daily_state.json")
        daily_state = state.get(self.state_key, {})
        
        updated = False
        
        # Parse sign-in response
        if "点卯" in text and ("成功" in text or "完成" in text):
            daily_state["sign_in_done"] = True
            logger.info("Daily sign-in completed")
            updated = True
        
        # Parse transmission response
        if "传功" in text and ("成功" in text or "完成" in text):
            count = daily_state.get("transmission_count", 0)
            daily_state["transmission_count"] = count + 1
            logger.info(f"Daily transmission completed ({count + 1}/3)")
            
            # Schedule next transmission if not done
            if count + 1 < 3 and self.config.enable_transmission:
                await self.command_queue.enqueue(
                    ".传功",
                    when=time.time() + 60,  # Wait 1 minute
                    priority=1,
                    dedupe_key=f"daily:transmission:{count+1}:{self.chat_id}"
                )
            updated = True
        
        # Parse greeting response
        if "问安" in text and ("成功" in text or "完成" in text):
            daily_state["greeting_done"] = True
            logger.info("Daily greeting completed")
            updated = True
        
        # Save state if updated
        if updated:
            state[self.state_key] = daily_state
            self.state_store.save("daily_state.json", state)
        
        return updated
    
    def get_status(self) -> Dict[str, Any]:
        """Get current daily routine status"""
        state = self.state_store.load("daily_state.json")
        daily_state = state.get(self.state_key, {})
        
        return {
            "date": daily_state.get("last_date"),
            "sign_in_done": daily_state.get("sign_in_done", False),
            "transmission_count": daily_state.get("transmission_count", 0),
            "greeting_done": daily_state.get("greeting_done", False)
        }
    
    async def reset_daily_state(self):
        """Reset daily state (called at midnight)"""
        state = self.state_store.load("daily_state.json")
        state[self.state_key] = {
            "last_date": date.today().isoformat(),
            "sign_in_done": False,
            "transmission_count": 0,
            "greeting_done": False
        }
        self.state_store.save("daily_state.json", state)
        logger.info("Daily state reset")
        
        # Re-schedule tasks
        await self._schedule_daily_tasks()
