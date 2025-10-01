"""
Periodic Tasks Module (周期任务)
Based on ARCHITECTURE.md section 4.4
"""
import logging
import time
from typing import Dict, Any, List

logger = logging.getLogger("tg-signer.periodic_tasks")


class PeriodicTasksModule:
    """
    Periodic Tasks Module
    
    Handles:
    - Qizhen (启阵)
    - Zhuzhen (助阵)
    - Wendao (问道)
    - Yindao (引道)
    - Yuanying (元婴)
    - Rift exploration (裂缝探索)
    """
    
    def __init__(
        self,
        config,
        state_store,
        command_queue,
        chat_id: int,
        account: str
    ):
        self.config = config.periodic
        self.state_store = state_store
        self.command_queue = command_queue
        self.chat_id = chat_id
        self.account = account
        
        # State key for this account/chat
        self.state_key = f"acct_{account}_chat_{chat_id}"
        
        # Task definitions with cooldowns (in seconds)
        self.tasks = {
            "qizhen": {
                "enabled": self.config.enable_qizhen,
                "command": ".启阵",
                "cooldown": 3600,  # 1 hour
                "priority": 3
            },
            "zhuzhen": {
                "enabled": self.config.enable_zhuzhen,
                "command": ".助阵",
                "cooldown": 3600,  # 1 hour
                "priority": 3
            },
            "wendao": {
                "enabled": self.config.enable_wendao,
                "command": ".问道",
                "cooldown": 7200,  # 2 hours
                "priority": 3
            },
            "yindao": {
                "enabled": self.config.enable_yindao,
                "command": ".引道",
                "cooldown": 7200,  # 2 hours
                "priority": 3
            },
            "yuanying": {
                "enabled": self.config.enable_yuanying,
                "command": ".元婴状态",
                "cooldown": 14400,  # 4 hours
                "priority": 3
            },
            "rift_explore": {
                "enabled": self.config.enable_rift_explore,
                "command": ".探索裂缝",
                "cooldown": 21600,  # 6 hours
                "priority": 3
            }
        }
    
    async def start(self):
        """Start periodic tasks automation"""
        logger.info("Starting periodic tasks module")
        await self._schedule_periodic_tasks()
    
    async def _schedule_periodic_tasks(self):
        """Schedule all enabled periodic tasks"""
        state = self.state_store.load("periodic_state.json")
        periodic_state = state.get(self.state_key, {})
        
        now = time.time()
        
        for task_name, task_info in self.tasks.items():
            if not task_info["enabled"]:
                continue
            
            last_run = periodic_state.get(f"{task_name}_last_run", 0)
            cooldown = task_info["cooldown"]
            
            # Check if task is ready to run
            if now - last_run >= cooldown:
                await self.command_queue.enqueue(
                    task_info["command"],
                    priority=task_info["priority"],
                    dedupe_key=f"periodic:{task_name}:{self.chat_id}"
                )
                logger.info(f"Scheduled periodic task: {task_name}")
            else:
                # Schedule for later
                next_run = last_run + cooldown
                await self.command_queue.enqueue(
                    task_info["command"],
                    when=next_run,
                    priority=task_info["priority"],
                    dedupe_key=f"periodic:{task_name}:scheduled:{self.chat_id}"
                )
                logger.debug(f"Scheduled {task_name} for {next_run - now:.0f} seconds from now")
        
        # Save state
        state[self.state_key] = periodic_state
        self.state_store.save("periodic_state.json", state)
    
    async def handle_message(self, message) -> bool:
        """Handle incoming message and update state"""
        if not message.text:
            return False
        
        text = message.text
        state = self.state_store.load("periodic_state.json")
        periodic_state = state.get(self.state_key, {})
        
        updated = False
        now = time.time()
        
        # Check each task
        for task_name, task_info in self.tasks.items():
            command_keyword = task_info["command"].replace(".", "")
            
            if command_keyword in text and ("成功" in text or "完成" in text):
                periodic_state[f"{task_name}_last_run"] = now
                logger.info(f"Periodic task completed: {task_name}")
                
                # Schedule next run
                next_run = now + task_info["cooldown"]
                await self.command_queue.enqueue(
                    task_info["command"],
                    when=next_run,
                    priority=task_info["priority"],
                    dedupe_key=f"periodic:{task_name}:next:{self.chat_id}"
                )
                
                updated = True
                break
        
        # Save state if updated
        if updated:
            state[self.state_key] = periodic_state
            self.state_store.save("periodic_state.json", state)
        
        return updated
    
    def get_status(self) -> Dict[str, Any]:
        """Get current periodic tasks status"""
        state = self.state_store.load("periodic_state.json")
        periodic_state = state.get(self.state_key, {})
        
        status = {}
        now = time.time()
        
        for task_name, task_info in self.tasks.items():
            last_run = periodic_state.get(f"{task_name}_last_run", 0)
            cooldown = task_info["cooldown"]
            next_run = last_run + cooldown if last_run > 0 else 0
            
            status[task_name] = {
                "enabled": task_info["enabled"],
                "last_run": last_run,
                "next_run": next_run,
                "ready": now >= next_run if next_run > 0 else True
            }
        
        return status
