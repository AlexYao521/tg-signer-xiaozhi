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
    
    def __init__(self, chat_id: int, account: str):
        self.chat_id = chat_id
        self.account = account
        self.state = DailyState()
    
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
        return not self.state.signin_done
    
    def should_greeting(self) -> bool:
        """是否应该执行每日问安"""
        return not self.state.greeting_done
    
    def should_transmission(self) -> bool:
        """是否应该执行宗门传功"""
        return self.state.transmission_count < 3
    
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
        
        # 解析点卯响应
        if "点卯成功" in text:
            self.state.signin_done = True
            self.state.last_signin_ts = time.time()
            logger.info("[每日] 点卯成功")
            return None
        
        if "今日已点卯" in text:
            self.state.signin_done = True
            logger.info("[每日] 今日已点卯")
            return None
        
        # 解析问安响应
        if "情缘增加" in text or "问安成功" in text:
            self.state.greeting_done = True
            self.state.last_greeting_ts = time.time()
            logger.info("[每日] 问安成功")
            return None
        
        if "今日已经问安" in text or "已问安" in text:
            self.state.greeting_done = True
            logger.info("[每日] 今日已问安")
            return None
        
        # 解析传功响应
        if "传功" in text:
            # 提取传功次数：今日已传功 X/3
            import re
            match = re.search(r'传功\s*(\d+)/3', text)
            if match:
                count = int(match.group(1))
                self.state.transmission_count = count
                self.state.last_transmission_ts = time.time()
                logger.info(f"[每日] 传功进度: {count}/3")
                
                if count < 3:
                    # 还可以继续传功，30-45秒后再次尝试
                    return "schedule_transmission"
                else:
                    logger.info("[每日] 今日传功已完成 3/3")
                    return None
        
        if "请明日再来" in text:
            self.state.transmission_count = 3
            logger.info("[每日] 传功已达上限")
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
        
        if self.should_signin():
            commands.append((".宗门点卯", 0, 0))  # P0优先级，立即执行
        
        if self.should_greeting():
            commands.append((".每日问安", 1, 5))  # P1优先级，延迟5秒
        
        if self.should_transmission():
            commands.append((".宗门传功", 1, 10))  # P1优先级，延迟10秒
        
        return commands
