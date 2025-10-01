"""
每日例行任务模块 (Daily Routine Module)
处理：宗门点卯、宗门传功、每日问安
"""
import logging
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .cooldown_parser import extract_cooldown_with_fallback

logger = logging.getLogger("tg-signer.daily")


@dataclass
class DailyState:
    """每日任务状态"""
    signin_done: bool = False
    greeting_done: bool = False
    transmission_count: int = 0
    last_signin_ts: float = 0
    last_greeting_ts: float = 0
    last_transmission_ts: float = 0
    last_message_id: Optional[int] = None  # 用于传功回复


class DailyRoutine:
    """
    每日例行任务管理器
    
    职责：
    - 宗门点卯（每日一次，过凌晨自动重置）
    - 每日问安（每日一次）
    - 宗门传功（每日最多3次，需要回复自己的消息）
    """
    
    def __init__(self, config, state_store, command_queue, chat_id: int, account: str):
        self.config = config.daily
        self.state_store = state_store
        self.command_queue = command_queue
        self.chat_id = chat_id
        self.account = account
        self.state_key = f"acct_{account}_chat_{chat_id}_daily"
        self.state = DailyState()
        
        # Load state
        state_data = state_store.load("daily_state.json")
        self.load_state(state_data.get(self.state_key, {}))
    
    def load_state(self, state_data: Dict[str, Any]):
        """从持久化数据加载状态"""
        if not state_data:
            return
        
        self.state.signin_done = state_data.get("signin_done", False)
        self.state.greeting_done = state_data.get("greeting_done", False)
        self.state.transmission_count = state_data.get("transmission_count", 0)
        self.state.last_signin_ts = state_data.get("last_signin_ts", 0)
        self.state.last_greeting_ts = state_data.get("last_greeting_ts", 0)
        self.state.last_transmission_ts = state_data.get("last_transmission_ts", 0)
        self.state.last_message_id = state_data.get("last_message_id")
        
        logger.info(
            f"[每日] 加载状态: 点卯={self.state.signin_done}, "
            f"问安={self.state.greeting_done}, 传功={self.state.transmission_count}/3"
        )
    
    def save_state(self) -> Dict[str, Any]:
        """保存状态到字典"""
        return {
            "signin_done": self.state.signin_done,
            "greeting_done": self.state.greeting_done,
            "transmission_count": self.state.transmission_count,
            "last_signin_ts": self.state.last_signin_ts,
            "last_greeting_ts": self.state.last_greeting_ts,
            "last_transmission_ts": self.state.last_transmission_ts,
            "last_message_id": self.state.last_message_id,
        }
    
    def reset_daily(self):
        """重置每日状态（午夜调用）"""
        logger.info("[每日] 重置每日任务状态")
        self.state.signin_done = False
        self.state.greeting_done = False
        self.state.transmission_count = 0
        self.state.last_message_id = None
    
    def should_signin(self) -> bool:
        """是否应该执行宗门点卯"""
        return self.config.enable_sign_in and not self.state.signin_done
    
    def should_greeting(self) -> bool:
        """是否应该执行每日问安"""
        return self.config.enable_greeting and not self.state.greeting_done
    
    def should_transmission(self) -> bool:
        """是否应该执行宗门传功"""
        return self.config.enable_transmission and self.state.transmission_count < 3
    
    def parse_response(self, text: str) -> Optional[str]:
        """
        解析频道响应，更新状态
        
        Args:
            text: 频道返回的文本
            
        Returns:
            下一步需要执行的指令，如果有的话
        """
        if not text:
            return None
        
        logger.debug(f"[每日] 解析响应: {text[:100]}")
        
        # 解析点卯响应
        if "点卯成功" in text:
            if not self.state.signin_done:
                self.state.signin_done = True
                self.state.last_signin_ts = time.time()
                logger.info("[每日] 点卯成功")
            else:
                logger.debug("[每日] 点卯已完成，忽略重复响应")
            return None
        
        if "今日已点卯" in text:
            if not self.state.signin_done:
                self.state.signin_done = True
                logger.info("[每日] 今日已点卯")
            else:
                logger.debug("[每日] 点卯已完成，忽略重复响应")
            return None
        
        # 解析问安响应
        if "情缘增加" in text or "问安成功" in text:
            if not self.state.greeting_done:
                self.state.greeting_done = True
                self.state.last_greeting_ts = time.time()
                logger.info("[每日] 问安成功")
            else:
                logger.debug("[每日] 问安已完成，忽略重复响应")
            return None
        
        if "今日已经问安" in text or "已问安" in text:
            if not self.state.greeting_done:
                self.state.greeting_done = True
                logger.info("[每日] 今日已问安")
            else:
                logger.debug("[每日] 问安已完成，忽略重复响应")
            return None
        
        # 解析传功响应
        if "传功" in text:
            # 提取传功次数：今日已传功 X/3
            import re
            match = re.search(r'传功\s*(\d+)/3', text)
            if match:
                count = int(match.group(1))
                old_count = self.state.transmission_count
                self.state.transmission_count = count
                self.state.last_transmission_ts = time.time()
                
                if count != old_count:
                    logger.info(f"[每日] 传功进度: {count}/3")
                else:
                    logger.debug(f"[每日] 传功进度未变化: {count}/3")
                
                if count < 3:
                    # 还可以继续传功，30-45秒后再次尝试
                    logger.info(f"[每日] 计划下次传功 (当前{count}/3)")
                    return "schedule_transmission"
                else:
                    logger.info("[每日] 今日传功已完成 3/3")
                    return None
        
        if "请明日再来" in text:
            if self.state.transmission_count < 3:
                self.state.transmission_count = 3
                logger.info("[每日] 传功已达上限")
            else:
                logger.debug("[每日] 传功已达上限（重复消息）")
            return None
        
        if "需回复" in text or "请回复" in text:
            logger.info("[每日] 传功需要回复消息")
            return "wait_for_reply"
        
        return None
    
    def update_last_message_id(self, message_id: int):
        """更新最后发送的消息ID（用于传功回复）"""
        self.state.last_message_id = message_id
    
    def get_next_commands(self) -> list[tuple[str, int, int]]:
        """
        获取下一步需要执行的指令
        
        Returns:
            列表of (command, priority, delay_seconds)
        """
        commands = []
        delay_offset = 0
        
        if self.should_signin():
            commands.append((".宗门点卯", 0, delay_offset))  # P0优先级
            delay_offset += 2
        
        if self.should_greeting():
            commands.append((".每日问安", 1, delay_offset))  # P1优先级
            delay_offset += 2
        
        if self.should_transmission():
            commands.append((".宗门传功", 1, delay_offset))  # P1优先级
            delay_offset += 2
        
        return commands
    
    async def start(self):
        """启动每日任务模块"""
        if not (self.config.enable_sign_in or self.config.enable_greeting or self.config.enable_transmission):
            logger.info("[每日] 所有每日任务均已禁用")
            return
        
        logger.info("[每日] 启动每日任务模块")
        
        # 调度初始任务
        for command, priority, delay in self.get_next_commands():
            await self.command_queue.enqueue(
                command,
                when=time.time() + delay,
                priority=priority,
                dedupe_key=f"daily:{command}:{self.chat_id}"
            )
    
    async def handle_message(self, message) -> bool:
        """处理消息"""
        if not message.text:
            return False
        
        text = message.text
        
        # 只处理包含关键词的消息
        if not any(keyword in text for keyword in ["点卯", "问安", "传功"]):
            return False
        
        logger.debug(f"[每日] 收到消息: {text[:50]}...")
        
        # 解析响应并更新状态
        next_action = self.parse_response(text)
        
        if next_action:
            # 保存状态
            self._save_state()
            
            if next_action == "schedule_transmission":
                # 继续调度传功任务
                import random
                delay = random.randint(30, 45)
                logger.info(f"[每日] 计划{delay}秒后继续传功")
                await self.command_queue.enqueue(
                    ".宗门传功",
                    when=time.time() + delay,
                    priority=1,
                    dedupe_key=f"daily:transmission:{self.chat_id}"
                )
            
            return True
        
        # 任何包含关键词的消息都要保存状态
        self._save_state()
        return True
    
    def _save_state(self):
        """保存状态到持久化存储"""
        state_data = self.state_store.load("daily_state.json")
        state_data[self.state_key] = self.save_state()
        self.state_store.save("daily_state.json", state_data)
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "signin_done": self.state.signin_done,
            "greeting_done": self.state.greeting_done,
            "transmission_count": self.state.transmission_count,
        }
