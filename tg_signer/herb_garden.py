"""
小药园自动化模块 (Herb Garden Module)
处理：小药园维护、采药、播种、兑换种子
"""
import logging
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from .cooldown_parser import parse_time_remaining
from .cooldown_config import SEED_MATURITY_HOURS

logger = logging.getLogger("tg-signer.herb")


class PlotState(Enum):
    """灵田状态"""
    MATURE = "mature"  # 已成熟 ✨
    PEST = "pest"  # 害虫侵扰 🐛
    WEED = "weed"  # 杂草横生 🌿
    DRY = "dry"  # 灵气干涸 🍂
    GROWING = "growing"  # 生长中 🌱
    IDLE = "idle"  # 空闲
    COOLDOWN = "cooldown"  # 冷却中


@dataclass
class Plot:
    """灵田地块"""
    idx: int
    state: PlotState
    seed: Optional[str] = None
    remain_seconds: Optional[int] = None
    mature_ts: Optional[float] = None


@dataclass
class HerbGardenState:
    """小药园状态"""
    plots: List[Plot] = None
    seed_inventory: Dict[str, int] = None
    last_scan_ts: float = 0
    last_maintenance_ts: float = 0
    last_harvest_ts: float = 0
    
    def __post_init__(self):
        if self.plots is None:
            self.plots = []
        if self.seed_inventory is None:
            self.seed_inventory = {}


class HerbGarden:
    """
    小药园自动化管理器
    
    职责：
    1. 扫描 .小药园 获取所有地块状态
    2. 执行维护动作（除虫、除草、浇水）
    3. 采药（一键采药）
    4. 播种（自动选择种子）
    5. 兑换种子（库存不足时）
    """
    
    def __init__(
        self, 
        chat_id: int, 
        account: str,
        default_seed: str = "凝血草种子",
        seed_configs: Dict[str, Dict] = None
    ):
        self.chat_id = chat_id
        self.account = account
        self.default_seed = default_seed
        self.seed_configs = seed_configs or {}
        self.state = HerbGardenState()
    
    def load_state(self, state_data: Dict[str, Any]):
        """从持久化数据加载状态"""
        if not state_data:
            return
        
        self.state.last_scan_ts = state_data.get("last_scan_ts", 0)
        self.state.last_maintenance_ts = state_data.get("last_maintenance_ts", 0)
        self.state.last_harvest_ts = state_data.get("last_harvest_ts", 0)
        self.state.seed_inventory = state_data.get("seed_inventory", {})
        
        plots_data = state_data.get("plots", [])
        self.state.plots.clear()
        for p_data in plots_data:
            self.state.plots.append(Plot(
                idx=p_data["idx"],
                state=PlotState(p_data["state"]),
                seed=p_data.get("seed"),
                remain_seconds=p_data.get("remain_seconds"),
                mature_ts=p_data.get("mature_ts")
            ))
        
        logger.info(f"[药园] 加载状态: {len(self.state.plots)}块灵田")
    
    def save_state(self) -> Dict[str, Any]:
        """保存状态到字典"""
        return {
            "last_scan_ts": self.state.last_scan_ts,
            "last_maintenance_ts": self.state.last_maintenance_ts,
            "last_harvest_ts": self.state.last_harvest_ts,
            "seed_inventory": self.state.seed_inventory,
            "plots": [
                {
                    "idx": p.idx,
                    "state": p.state.value,
                    "seed": p.seed,
                    "remain_seconds": p.remain_seconds,
                    "mature_ts": p.mature_ts
                }
                for p in self.state.plots
            ]
        }
    
    def should_scan(self) -> bool:
        """是否应该扫描小药园"""
        now = time.time()
        # 检查是否有地块即将成熟
        if self.state.plots:
            for plot in self.state.plots:
                if plot.mature_ts and plot.mature_ts <= now + 120:  # 2分钟内成熟
                    return True
        
        # 否则使用默认扫描间隔（15分钟）
        return now - self.state.last_scan_ts > 900
    
    def parse_scan_response(self, text: str) -> List[tuple[str, int, int]]:
        """
        解析小药园扫描响应
        
        Returns:
            指令列表 [(command, priority, delay_seconds)]
        """
        if not text:
            return []
        
        self.state.last_scan_ts = time.time()
        self.state.plots.clear()
        
        # 解析每行地块状态
        # 格式示例：
        # 1号灵田: 凝血草种子 - 已成熟 ✨
        # 2号灵田: 清灵草种子 - 生长中 🌱 (剩余: 2小时15分钟)
        # 3号灵田: 害虫侵扰 🐛
        # 4号灵田: 空闲
        
        import re
        lines = text.split('\n')
        
        for line in lines:
            match = re.match(
                r'(\d+)号灵田[:：]\s*(?:([^\s\-]+)\s*[-－]\s*)?(.+?)(?:\s*\(剩余[:：]\s*([^\)]+)\))?$',
                line.strip()
            )
            
            if not match:
                continue
            
            idx = int(match.group(1))
            seed = match.group(2)
            state_text = match.group(3)
            remain_text = match.group(4)
            
            state = self._parse_plot_state(state_text)
            remain_seconds = None
            mature_ts = None
            
            if remain_text and state == PlotState.GROWING:
                remain_seconds = parse_time_remaining(remain_text)
                if remain_seconds:
                    mature_ts = time.time() + remain_seconds
            
            plot = Plot(
                idx=idx,
                state=state,
                seed=seed,
                remain_seconds=remain_seconds,
                mature_ts=mature_ts
            )
            self.state.plots.append(plot)
            
            logger.info(f"[药园] {idx}号田: {seed} - {state.value}")
        
        # 生成维护和操作指令
        return self._generate_commands()
    
    def _parse_plot_state(self, state_text: str) -> PlotState:
        """解析地块状态"""
        if "已成熟" in state_text or "成熟" in state_text:
            return PlotState.MATURE
        if "害虫" in state_text or "虫害" in state_text:
            return PlotState.PEST
        if "杂草" in state_text:
            return PlotState.WEED
        if "干涸" in state_text or "缺水" in state_text:
            return PlotState.DRY
        if "生长中" in state_text or "生长" in state_text:
            return PlotState.GROWING
        if "空闲" in state_text:
            return PlotState.IDLE
        if "冷却" in state_text:
            return PlotState.COOLDOWN
        
        return PlotState.IDLE
    
    def _generate_commands(self) -> List[tuple[str, int, int]]:
        """根据地块状态生成操作指令"""
        commands = []
        
        # 统计各种状态的地块
        has_pest = any(p.state == PlotState.PEST for p in self.state.plots)
        has_weed = any(p.state == PlotState.WEED for p in self.state.plots)
        has_dry = any(p.state == PlotState.DRY for p in self.state.plots)
        has_mature = any(p.state == PlotState.MATURE for p in self.state.plots)
        idle_plots = [p for p in self.state.plots if p.state == PlotState.IDLE]
        
        # P0: 维护任务（必须在采药前完成）
        if has_pest:
            commands.append((".除虫", 0, 1))
        if has_weed:
            commands.append((".除草", 0, 1))
        if has_dry:
            commands.append((".浇水", 0, 1))
        
        # P1: 采药
        if has_mature:
            # 维护任务完成后再采药
            delay = 5 if (has_pest or has_weed or has_dry) else 1
            commands.append((".采药", 1, delay))
        
        # P1: 播种（在采药成功后的回调中处理，这里不直接生成）
        # 但我们可以检查种子库存
        if idle_plots:
            logger.info(f"[药园] 有{len(idle_plots)}块空闲灵田待播种")
        
        return commands
    
    def parse_maintenance_response(self, text: str, action: str) -> bool:
        """
        解析维护操作响应
        
        Args:
            text: 响应文本
            action: 动作名称（除虫、除草、浇水）
            
        Returns:
            是否成功
        """
        if f"一键{action}完成" in text or f"{action}成功" in text:
            self.state.last_maintenance_ts = time.time()
            logger.info(f"[药园] {action}成功")
            return True
        
        if f"没有需要【{action}】" in text or f"无需{action}" in text:
            logger.info(f"[药园] 无需{action}")
            return False
        
        return False
    
    def parse_harvest_response(self, text: str) -> bool:
        """解析采药响应"""
        if "一键采药完成" in text or "采药成功" in text:
            self.state.last_harvest_ts = time.time()
            logger.info("[药园] 采药成功")
            # 将成熟的地块标记为空闲
            for plot in self.state.plots:
                if plot.state == PlotState.MATURE:
                    plot.state = PlotState.IDLE
                    plot.seed = None
            return True
        
        if "没有需要【采药】" in text or "无成熟" in text:
            logger.info("[药园] 无成熟药材")
            return False
        
        return False
    
    def generate_planting_commands(self) -> List[tuple[str, int, int]]:
        """
        生成播种指令（在采药成功后调用）
        
        Returns:
            播种指令列表
        """
        idle_plots = [p for p in self.state.plots if p.state == PlotState.IDLE]
        
        if not idle_plots:
            return []
        
        commands = []
        seed = self.default_seed
        
        # 检查种子库存（简化版，实际应该从状态中读取）
        for i, plot in enumerate(idle_plots):
            # 播种指令
            command = f".播种 {plot.idx} {seed}"
            delay = i * 2  # 每个播种间隔2秒
            commands.append((command, 1, delay))
        
        logger.info(f"[药园] 生成{len(commands)}个播种指令")
        return commands
    
    def parse_planting_response(self, text: str, plot_idx: int) -> bool:
        """解析播种响应"""
        if "播下" in text or "种植成功" in text:
            # 更新地块状态为生长中
            for plot in self.state.plots:
                if plot.idx == plot_idx:
                    plot.state = PlotState.GROWING
                    plot.seed = self.default_seed
                    logger.info(f"[药园] {plot_idx}号田播种成功")
            return True
        
        return False
