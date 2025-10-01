"""
星宫观星台模块 (Star Observation Module)
处理：观星台、安抚星辰、牵引星辰、收集精华
"""
import logging
import time
import random
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from .cooldown_parser import parse_time_remaining
from .cooldown_config import get_star_pull_cooldown

logger = logging.getLogger("tg-signer.star")


class StarState(Enum):
    """星辰状态"""
    READY = "ready"  # 精华已成
    IDLE = "idle"  # 空闲
    CONDENSING = "condensing"  # 凝聚中
    AGITATED = "agitated"  # 星光黯淡/元磁紊乱/躁动/狂暴


@dataclass
class StarPlate:
    """引星盘状态"""
    idx: int  # 编号
    star_name: str  # 星辰名称
    state: StarState
    remain_seconds: Optional[int] = None  # 剩余时间（凝聚中）


@dataclass
class StarObservationState:
    """星宫状态"""
    plates: List[StarPlate] = None
    last_pacify_ts: float = 0
    sequence_index: int = 0
    last_scan_ts: float = 0
    
    def __post_init__(self):
        if self.plates is None:
            self.plates = []


class StarObservation:
    """
    星宫观星台管理器
    
    核心逻辑：
    1. **永远先执行 .安抚星辰，再执行 .观星台**
    2. 解析观星台状态，决定下一步动作
    3. 牵引星辰按序列轮转
    """
    
    def __init__(self, chat_id: int, account: str, star_sequence: List[str] = None):
        self.chat_id = chat_id
        self.account = account
        self.star_sequence = star_sequence or ["天雷星", "赤血星", "庚金星"]
        self.state = StarObservationState()
    
    def load_state(self, state_data: Dict[str, Any]):
        """从持久化数据加载状态"""
        if not state_data:
            return
        
        self.state.last_pacify_ts = state_data.get("last_pacify_ts", 0)
        self.state.sequence_index = state_data.get("sequence_index", 0)
        self.state.last_scan_ts = state_data.get("last_scan_ts", 0)
        
        logger.info(f"[星宫] 加载状态: 上次安抚={self.state.last_pacify_ts}")
    
    def save_state(self) -> Dict[str, Any]:
        """保存状态到字典"""
        return {
            "last_pacify_ts": self.state.last_pacify_ts,
            "sequence_index": self.state.sequence_index,
            "last_scan_ts": self.state.last_scan_ts,
            "plates": [
                {
                    "idx": p.idx,
                    "star_name": p.star_name,
                    "state": p.state.value,
                    "remain_seconds": p.remain_seconds
                }
                for p in self.state.plates
            ] if self.state.plates else []
        }
    
    def should_start_observation(self) -> bool:
        """
        判断是否应该启动星宫流程
        
        启动策略：先尝试 .安抚星辰
        """
        # 检查上次安抚时间，避免频繁安抚
        now = time.time()
        if now - self.state.last_pacify_ts < 300:  # 5分钟内不重复安抚
            return False
        return True
    
    def get_startup_commands(self) -> List[tuple[str, int, int]]:
        """
        获取启动指令序列
        
        Returns:
            列表of (command, priority, delay_seconds)
        """
        # 核心设计：永远先安抚，再观星台
        return [
            (".安抚星辰", 0, 0),  # P0优先级，立即执行
            (".观星台", 1, random.randint(3, 6))  # P1优先级，3-6秒后执行
        ]
    
    def parse_pacify_response(self, text: str) -> Optional[str]:
        """
        解析安抚星辰响应
        
        Args:
            text: 频道返回文本
            
        Returns:
            下一步指令
        """
        if not text:
            return None
        
        if "成功安抚" in text or "安抚成功" in text:
            self.state.last_pacify_ts = time.time()
            logger.info("[星宫] 安抚星辰成功")
            # 5-8秒后扫描观星台
            return "schedule_scan"
        
        if "没有需要安抚" in text or "无需安抚" in text:
            logger.info("[星宫] 无需安抚星辰")
            # 2-4秒后扫描观星台
            return "schedule_scan_fast"
        
        # 失败或其他情况，指数退避重试
        logger.warning(f"[星宫] 安抚响应未识别: {text[:50]}")
        return None
    
    def parse_observation_response(self, text: str) -> List[tuple[str, int, int]]:
        """
        解析观星台响应，生成后续指令
        
        Args:
            text: 频道返回文本
            
        Returns:
            指令列表 [(command, priority, delay_seconds)]
        """
        if not text:
            return []
        
        self.state.last_scan_ts = time.time()
        self.state.plates.clear()
        
        # 解析观星台状态行
        # 格式：1号引星盘: 天雷星 - 精华已成
        # 格式：2号引星盘: 赤血星 - 凝聚中 (剩余: 3小时20分钟)
        # 格式：3号引星盘: 空闲 - 可牵引
        # 格式：4号引星盘: 庚金星 - 星光黯淡
        
        import re
        lines = text.split('\n')
        
        commands = []
        has_agitated = False
        
        for line in lines:
            # 匹配引星盘状态
            match = re.match(
                r'(\d+)号引星盘[:：]\s*(?:([^\s\-]+)\s*[-－]\s*)?(.+?)(?:\s*\(剩余[:：]\s*([^\)]+)\))?$',
                line.strip()
            )
            
            if not match:
                continue
            
            idx = int(match.group(1))
            star_name = match.group(2) or "未知"
            state_text = match.group(3)
            remain_text = match.group(4)
            
            # 判断状态
            state = self._parse_star_state(state_text)
            remain_seconds = None
            
            if remain_text:
                remain_seconds = parse_time_remaining(remain_text)
            
            plate = StarPlate(
                idx=idx,
                star_name=star_name,
                state=state,
                remain_seconds=remain_seconds
            )
            self.state.plates.append(plate)
            
            logger.info(f"[星宫] {idx}号盘: {star_name} - {state.value} - 剩余{remain_seconds}秒")
            
            # 生成对应指令
            if state == StarState.READY:
                # 精华已成，立即收集
                commands.append((".收集精华", 0, random.randint(1, 3)))
            
            elif state == StarState.AGITATED:
                # 星光黯淡/躁动，需要安抚（但我们已经在启动时安抚过了）
                has_agitated = True
                logger.warning(f"[星宫] {idx}号盘星辰躁动: {star_name}")
            
            elif state == StarState.IDLE:
                # 空闲，可以牵引
                next_star = self._get_next_star()
                if next_star:
                    command = f".牵引星辰 {idx} {next_star}"
                    commands.append((command, 1, random.randint(3, 8)))
                    logger.info(f"[星宫] 计划牵引: {idx}号盘 -> {next_star}")
            
            elif state == StarState.CONDENSING:
                # 凝聚中，等待
                if remain_seconds:
                    logger.info(f"[星宫] {idx}号盘凝聚中，剩余{remain_seconds}秒")
        
        # 如果有躁动的星辰但启动时已安抚，说明可能还有未解决的
        if has_agitated:
            logger.info("[星宫] 检测到躁动星辰，可能需要再次安抚")
        
        return commands
    
    def _parse_star_state(self, state_text: str) -> StarState:
        """解析星辰状态文本"""
        if "精华已成" in state_text or "可收集" in state_text:
            return StarState.READY
        
        if "星光黯淡" in state_text or "元磁紊乱" in state_text or \
           "躁动" in state_text or "狂暴" in state_text:
            return StarState.AGITATED
        
        if "凝聚中" in state_text or "凝聚" in state_text:
            return StarState.CONDENSING
        
        if "空闲" in state_text or "可牵引" in state_text:
            return StarState.IDLE
        
        # 默认认为是空闲
        return StarState.IDLE
    
    def _get_next_star(self) -> str:
        """获取序列中下一个要牵引的星辰"""
        if not self.star_sequence:
            return "天雷星"  # 默认星辰
        
        star = self.star_sequence[self.state.sequence_index]
        self.state.sequence_index = (self.state.sequence_index + 1) % len(self.star_sequence)
        return star
    
    def parse_collect_response(self, text: str) -> Optional[str]:
        """解析收集精华响应"""
        if "收集成功" in text or "获得" in text:
            logger.info("[星宫] 收集精华成功")
            # 3-6秒后再次扫描观星台
            return "schedule_scan"
        
        if "没有" in text or "无" in text:
            logger.info("[星宫] 无精华可收集")
        
        return None
    
    def parse_pull_response(self, text: str, star_name: str) -> Optional[int]:
        """
        解析牵引星辰响应
        
        Returns:
            冷却时间（秒），如果成功的话
        """
        if "牵引成功" in text or "开始牵引" in text:
            cooldown = get_star_pull_cooldown(star_name)
            logger.info(f"[星宫] 牵引{star_name}成功，冷却{cooldown}秒")
            return cooldown
        
        return None
