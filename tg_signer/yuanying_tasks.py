"""
元婴任务模块 (YuanYing Tasks Module)
处理元婴出窍和状态检查
Based on ARCHITECTURE.md section 4.4 (Periodic Tasks)
"""
import logging
import time
from typing import Optional, Dict, Any

from .cooldown_parser import extract_cooldown_with_fallback, parse_time_remaining
from .cooldown_config import PERIODIC_COOLDOWNS

logger = logging.getLogger("tg-signer.yuanying")


class YuanYingTasks:
    """
    元婴任务管理器 (Module-style)
    
    管理任务：
    - .元婴状态 (查询元婴状态)
    - .元婴出窍 (元婴出窍)
    
    状态类型：
    1. 元神归窍 - 元婴满载而归，可以立即出窍
    2. 元神出窍 - 元婴正在外游历，显示归来倒计时
    3. 窍中温养 - 元婴在体内温养，可能可以出窍
    
    This module follows the same pattern as other modules (HerbGarden, StarObservatory, etc.)
    and is controlled by config.periodic.enable_yuanying
    """
    
    def __init__(
        self,
        config,
        state_store,
        command_queue,
        chat_id: int,
        account: str
    ):
        self.config = config.periodic  # Access periodic config
        self.state_store = state_store
        self.command_queue = command_queue
        self.chat_id = chat_id
        self.account = account
        
        # State key for this account/chat
        self.state_key = f"acct_{account}_chat_{chat_id}"
    
    async def start(self):
        """Start yuanying tasks automation"""
        if not self.config.enable_yuanying:
            logger.info("YuanYing module disabled")
            return
        
        logger.info("Starting YuanYing module")
        await self._schedule_yuanying_check()
    
    async def _schedule_yuanying_check(self):
        """Schedule initial yuanying status check"""
        state = self.state_store.load("yuanying_state.json")
        yuanying_state = state.get(self.state_key, {})
        
        now = time.time()
        next_check = yuanying_state.get("next_check_ts", 0)
        
        # Check if we should check status now
        if now >= next_check:
            await self.command_queue.enqueue(
                ".元婴状态",
                priority=2,
                dedupe_key=f"yuanying:check:{self.chat_id}"
            )
            logger.info("Scheduled yuanying status check")
        else:
            # Schedule for later
            await self.command_queue.enqueue(
                ".元婴状态",
                when=next_check,
                priority=2,
                dedupe_key=f"yuanying:check:scheduled:{self.chat_id}"
            )
            logger.debug(f"Scheduled yuanying check for {next_check - now:.0f} seconds from now")
    
    async def handle_message(self, message) -> bool:
        """
        Handle incoming message and update state.
        
        Returns:
            True if message was handled, False otherwise
        """
        if not message.text:
            return False
        
        text = message.text
        
        # Parse yuanying status response
        if "元婴状态" in text or "元神" in text:
            await self._parse_status_response(text)
            return True
        
        # Parse yuanying chuxiao response
        if "元婴出窍" in text or "元婴离体" in text or "云游" in text:
            await self._parse_chuxiao_response(text)
            return True
        
        return False
    
    async def _parse_status_response(self, text: str):
        """
        解析 .元婴状态 的响应
        
        Args:
            text: 频道返回文本
        """
        if not text:
            return
        
        state = self.state_store.load("yuanying_state.json")
        yuanying_state = state.get(self.state_key, {})
        
        now = time.time()
        yuanying_state["last_check_ts"] = now
        
        # Default cooldown for next check
        cooldown_seconds = 30 * 60  # 30 minutes
        
        # 识别状态类型
        if "【元神归窍】" in text or "元婴满载而归" in text or "归窍" in text:
            # 状态1：元神归窍 - 可以立即出窍
            yuanying_state["status"] = "归窍"
            yuanying_state["can_chuxiao"] = True
            cooldown_seconds = 30  # 30 seconds before chuxiao
            logger.info("[元婴] 识别状态: 元神归窍 - 可以立即出窍")
            
            # Schedule chuxiao
            await self.command_queue.enqueue(
                ".元婴出窍",
                when=now + 30,
                priority=2,
                dedupe_key=f"yuanying:chuxiao:{self.chat_id}"
            )
            
        elif "元神出窍" in text or "状态: 元神出窍" in text:
            # 状态2：元神出窍 - 正在外游历
            yuanying_state["status"] = "出窍"
            yuanying_state["can_chuxiao"] = False
            
            # 提取归来倒计时
            countdown = parse_time_remaining(text)
            if countdown:
                yuanying_state["return_countdown_seconds"] = countdown
                # 在归来前2分钟安排预扫
                cooldown_seconds = max(countdown - 120, 60)
                logger.info(f"[元婴] 识别状态: 元神出窍 - 归来倒计时{countdown}秒")
            else:
                # 没有找到倒计时，使用默认查询间隔
                logger.info("[元婴] 识别状态: 元神出窍 - 未找到倒计时")
            
        elif "窍中温养" in text or "状态: 窍中温养" in text:
            # 状态3：窍中温养 - 可能可以出窍
            yuanying_state["status"] = "温养"
            
            # 检查是否可以出窍
            if "可以出窍" in text or "已完成温养" in text:
                yuanying_state["can_chuxiao"] = True
                cooldown_seconds = 30  # 30秒后出窍
                logger.info("[元婴] 识别状态: 窍中温养 - 可以出窍")
                
                # Schedule chuxiao
                await self.command_queue.enqueue(
                    ".元婴出窍",
                    when=now + 30,
                    priority=2,
                    dedupe_key=f"yuanying:chuxiao:{self.chat_id}"
                )
            else:
                # 检查是否在冷却中
                yuanying_state["can_chuxiao"] = False
                cooldown = extract_cooldown_with_fallback(text, "元婴出窍")
                cooldown_seconds = cooldown
                logger.info(f"[元婴] 识别状态: 窍中温养 - 冷却中({cooldown}秒)")
        
        else:
            # 未识别的状态
            logger.warning(f"[元婴] 未识别的状态文本: {text[:100]}")
            yuanying_state["status"] = "unknown"
        
        # Schedule next check
        yuanying_state["next_check_ts"] = now + cooldown_seconds
        await self.command_queue.enqueue(
            ".元婴状态",
            when=now + cooldown_seconds,
            priority=2,
            dedupe_key=f"yuanying:check:next:{self.chat_id}"
        )
        
        # Save state
        state[self.state_key] = yuanying_state
        self.state_store.save("yuanying_state.json", state)
    
    async def _parse_chuxiao_response(self, text: str):
        """
        解析 .元婴出窍 的响应
        
        Args:
            text: 频道返回文本
        """
        if not text:
            return
        
        state = self.state_store.load("yuanying_state.json")
        yuanying_state = state.get(self.state_key, {})
        
        now = time.time()
        
        # 识别成功标识
        success_keywords = ["云游", "出窍成功", "元婴离体"]
        if any(kw in text for kw in success_keywords):
            # Success - yuanying is now out
            yuanying_state["status"] = "出窍"
            yuanying_state["can_chuxiao"] = False
            yuanying_state["last_chuxiao_ts"] = now
            
            # 提取冷却时间 (例如: "云游 8 小时")
            cooldown = extract_cooldown_with_fallback(text, "元婴出窍")
            yuanying_state["chuxiao_cooldown"] = cooldown
            
            # Schedule status check before return (2 minutes early)
            next_check = now + cooldown - 120
            yuanying_state["next_check_ts"] = next_check
            
            await self.command_queue.enqueue(
                ".元婴状态",
                when=next_check,
                priority=2,
                dedupe_key=f"yuanying:check:before_return:{self.chat_id}"
            )
            
            logger.info(f"[元婴] 出窍成功，冷却{cooldown}秒，将在归来前2分钟检查")
        
        else:
            # Check if in cooldown
            if "冷却" in text or "请在" in text or "后再" in text:
                cooldown = extract_cooldown_with_fallback(text, "元婴出窍")
                yuanying_state["chuxiao_cooldown"] = cooldown
                
                # Schedule status check after cooldown
                next_check = now + cooldown
                yuanying_state["next_check_ts"] = next_check
                
                await self.command_queue.enqueue(
                    ".元婴状态",
                    when=next_check,
                    priority=2,
                    dedupe_key=f"yuanying:check:after_cooldown:{self.chat_id}"
                )
                
                logger.info(f"[元婴] 出窍失败，冷却{cooldown}秒")
            else:
                logger.warning(f"[元婴] 未识别的出窍响应: {text[:100]}")
        
        # Save state
        state[self.state_key] = yuanying_state
        self.state_store.save("yuanying_state.json", state)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current yuanying status"""
        state = self.state_store.load("yuanying_state.json")
        yuanying_state = state.get(self.state_key, {})
        
        return {
            "enabled": self.config.enable_yuanying,
            "status": yuanying_state.get("status", "unknown"),
            "can_chuxiao": yuanying_state.get("can_chuxiao", False),
            "last_check": yuanying_state.get("last_check_ts"),
            "next_check": yuanying_state.get("next_check_ts"),
            "last_chuxiao": yuanying_state.get("last_chuxiao_ts"),
            "return_countdown": yuanying_state.get("return_countdown_seconds", 0)
        }

