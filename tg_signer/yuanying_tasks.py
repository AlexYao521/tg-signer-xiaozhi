"""
元婴任务模块 (YuanYing Tasks Module)
处理元婴出窍和状态检查
"""
import logging
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from .cooldown_parser import extract_cooldown_with_fallback, parse_time_remaining
from .cooldown_config import PERIODIC_COOLDOWNS

logger = logging.getLogger("tg-signer.yuanying")


@dataclass
class YuanYingState:
    """元婴状态"""
    status: str = "unknown"  # 可能值: 出窍, 归窍, 温养, unknown
    last_check_ts: float = 0
    chuxiao_ts: float = 0  # 上次出窍时间
    return_countdown_seconds: int = 0  # 归来倒计时(秒)
    next_check_ts: float = 0
    next_chuxiao_ts: float = 0


class YuanYingTasks:
    """
    元婴任务管理器
    
    管理任务：
    - .元婴状态 (查询元婴状态)
    - .元婴出窍 (元婴出窍)
    
    状态类型：
    1. 元神归窍 - 元婴满载而归，可以立即出窍
    2. 元神出窍 - 元婴正在外游历，显示归来倒计时
    3. 窍中温养 - 元婴在体内温养，可能可以出窍
    """
    
    def __init__(self, chat_id: int, account: str, enabled: bool = True):
        self.chat_id = chat_id
        self.account = account
        self.enabled = enabled
        self.state = YuanYingState()
    
    def load_state(self, state_data: Dict[str, Any]):
        """从持久化数据加载状态"""
        if not state_data:
            return
        
        self.state.status = state_data.get("status", "unknown")
        self.state.last_check_ts = state_data.get("last_check_ts", 0)
        self.state.chuxiao_ts = state_data.get("chuxiao_ts", 0)
        self.state.return_countdown_seconds = state_data.get("return_countdown_seconds", 0)
        self.state.next_check_ts = state_data.get("next_check_ts", 0)
        self.state.next_chuxiao_ts = state_data.get("next_chuxiao_ts", 0)
        
        logger.info(f"[元婴] 加载状态: status={self.state.status}")
    
    def save_state(self) -> Dict[str, Any]:
        """保存状态到字典"""
        return {
            "status": self.state.status,
            "last_check_ts": self.state.last_check_ts,
            "chuxiao_ts": self.state.chuxiao_ts,
            "return_countdown_seconds": self.state.return_countdown_seconds,
            "next_check_ts": self.state.next_check_ts,
            "next_chuxiao_ts": self.state.next_chuxiao_ts,
        }
    
    def should_check_status(self) -> bool:
        """检查是否应该查询元婴状态"""
        if not self.enabled:
            return False
        
        now = time.time()
        # 如果从未查询过，或者超过查询间隔，则需要查询
        return now >= self.state.next_check_ts
    
    def should_chuxiao(self) -> bool:
        """检查是否应该执行元婴出窍"""
        if not self.enabled:
            return False
        
        now = time.time()
        # 如果元婴状态允许出窍，且过了冷却时间
        return now >= self.state.next_chuxiao_ts and self.state.status in ["归窍", "温养"]
    
    def get_ready_tasks(self) -> list[tuple[str, int, int]]:
        """
        获取可以执行的任务
        
        Returns:
            列表of (command, priority, delay_seconds)
        """
        tasks = []
        
        # 优先级：状态查询 > 出窍
        if self.should_check_status():
            tasks.append((".元婴状态", 1, 0))
            logger.info("[元婴] 任务就绪: .元婴状态")
        
        if self.should_chuxiao():
            tasks.append((".元婴出窍", 1, 0))
            logger.info("[元婴] 任务就绪: .元婴出窍")
        
        return tasks
    
    def parse_status_response(self, text: str) -> Optional[Dict[str, Any]]:
        """
        解析 .元婴状态 的响应
        
        Args:
            text: 频道返回文本
            
        Returns:
            解析结果字典，包含状态和后续动作
        """
        if not text:
            return None
        
        result = {
            "status": "unknown",
            "next_actions": [],
            "cooldown_seconds": 30 * 60,  # 默认30分钟后再查询
        }
        
        # 识别状态类型
        if "【元神归窍】" in text or "元婴满载而归" in text:
            # 状态1：元神归窍 - 可以立即出窍
            result["status"] = "归窍"
            result["next_actions"] = [".元婴出窍"]
            result["cooldown_seconds"] = 30  # 30秒后出窍
            logger.info("[元婴] 识别状态: 元神归窍 - 可以立即出窍")
            
        elif "元神出窍" in text or "状态: 元神出窍" in text:
            # 状态2：元神出窍 - 正在外游历
            result["status"] = "出窍"
            
            # 提取归来倒计时
            # 匹配格式: "归来倒计时: 3小时20分钟" 或 "剩余: 2小时30分钟"
            countdown = parse_time_remaining(text)
            if countdown:
                result["return_countdown_seconds"] = countdown
                # 在归来前2分钟安排预扫
                result["cooldown_seconds"] = max(countdown - 120, 60)
                logger.info(f"[元婴] 识别状态: 元神出窍 - 归来倒计时{countdown}秒")
            else:
                # 没有找到倒计时，使用默认查询间隔
                result["cooldown_seconds"] = 30 * 60
                logger.info("[元婴] 识别状态: 元神出窍 - 未找到倒计时")
            
        elif "窍中温养" in text or "状态: 窍中温养" in text:
            # 状态3：窍中温养 - 可能可以出窍
            result["status"] = "温养"
            
            # 检查是否可以出窍
            if "可以出窍" in text or "已完成温养" in text:
                result["next_actions"] = [".元婴出窍"]
                result["cooldown_seconds"] = 30  # 30秒后出窍
                logger.info("[元婴] 识别状态: 窍中温养 - 可以出窍")
            else:
                # 检查是否在冷却中
                cooldown = extract_cooldown_with_fallback(text, "元婴出窍")
                result["cooldown_seconds"] = cooldown
                logger.info(f"[元婴] 识别状态: 窍中温养 - 冷却中({cooldown}秒)")
        
        else:
            # 未识别的状态
            logger.warning(f"[元婴] 未识别的状态文本: {text[:100]}")
            result["cooldown_seconds"] = 30 * 60  # 默认30分钟后再查询
        
        # 更新内部状态
        now = time.time()
        self.state.status = result["status"]
        self.state.last_check_ts = now
        self.state.return_countdown_seconds = result.get("return_countdown_seconds", 0)
        self.state.next_check_ts = now + result["cooldown_seconds"]
        
        return result
    
    def parse_chuxiao_response(self, text: str) -> Optional[Dict[str, Any]]:
        """
        解析 .元婴出窍 的响应
        
        Args:
            text: 频道返回文本
            
        Returns:
            解析结果字典
        """
        if not text:
            return None
        
        result = {
            "success": False,
            "cooldown_seconds": 8 * 3600,  # 默认8小时
        }
        
        # 识别成功标识
        success_keywords = ["云游", "出窍成功", "元婴离体"]
        if any(kw in text for kw in success_keywords):
            result["success"] = True
            
            # 提取冷却时间 (例如: "云游 8 小时")
            cooldown = extract_cooldown_with_fallback(text, "元婴出窍")
            result["cooldown_seconds"] = cooldown
            
            # 更新状态
            now = time.time()
            self.state.status = "出窍"
            self.state.chuxiao_ts = now
            self.state.next_chuxiao_ts = now + cooldown
            # 在归来前2分钟安排状态查询
            self.state.next_check_ts = now + cooldown - 120
            
            logger.info(f"[元婴] 出窍成功，冷却{cooldown}秒")
        
        else:
            # 检查是否在冷却中
            if "冷却" in text or "请在" in text or "后再" in text:
                cooldown = extract_cooldown_with_fallback(text, "元婴出窍")
                result["cooldown_seconds"] = cooldown
                
                now = time.time()
                self.state.next_chuxiao_ts = now + cooldown
                
                logger.info(f"[元婴] 出窍失败，冷却{cooldown}秒")
            else:
                logger.warning(f"[元婴] 未识别的出窍响应: {text[:100]}")
        
        return result
    
    def mark_guiqiao(self):
        """标记元婴归窍（被动监听到归窍消息时调用）"""
        now = time.time()
        self.state.status = "归窍"
        self.state.next_chuxiao_ts = now + 30  # 30秒后可以出窍
        self.state.next_check_ts = now + 30
        
        logger.info("[元婴] 标记元神归窍，30秒后可出窍")
