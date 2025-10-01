"""
周期任务模块 (Periodic Tasks Module)
处理：闭关修炼、引道、启阵、问道、探寻裂缝等
"""
import logging
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from .cooldown_parser import extract_cooldown_with_fallback
from .cooldown_config import PERIODIC_COOLDOWNS

logger = logging.getLogger("tg-signer.periodic")


@dataclass
class TaskCooldown:
    """任务冷却状态"""
    task_name: str
    last_execute_ts: float = 0
    cooldown_seconds: int = 0
    next_execute_ts: float = 0


@dataclass
class PeriodicState:
    """周期任务状态"""
    cooldowns: Dict[str, TaskCooldown] = field(default_factory=dict)


class PeriodicTasks:
    """
    周期任务管理器
    
    管理任务：
    - 闭关修炼（16分钟）
    - 引道（12小时）
    - 启阵（12小时）
    - 问道（12小时）
    - 探寻裂缝（12小时）
    """
    
    TASKS = {
        "闭关修炼": ".闭关修炼",
        "引道": ".引道 水",
        "启阵": ".启阵",
        "问道": ".问道",
        "探寻裂缝": ".探寻裂缝",
        "元婴出窍": ".元婴出窍",
        "元婴状态": ".元婴状态",
    }
    
    def __init__(self, config, state_store, command_queue, chat_id: int, account: str):
        self.config = config.periodic
        self.state_store = state_store
        self.command_queue = command_queue
        self.chat_id = chat_id
        self.account = account
        self.state_key = f"acct_{account}_chat_{chat_id}_periodic"
        
        # 提取启用的任务
        self.enabled_tasks = {
            "biguan": getattr(self.config, "enable_biguan", True),
            "yindao": getattr(self.config, "enable_yindao", True),
            "qizhen": getattr(self.config, "enable_qizhen", True),
            "wendao": getattr(self.config, "enable_wendao", True),
            "rift_explore": getattr(self.config, "enable_rift_explore", True),
            "yuanying": getattr(self.config, "enable_yuanying", True),
        }
        
        self.state = PeriodicState()
        
        # 初始化所有任务的冷却状态
        for task_name in self.TASKS.keys():
            if task_name not in self.state.cooldowns:
                self.state.cooldowns[task_name] = TaskCooldown(
                    task_name=task_name,
                    cooldown_seconds=PERIODIC_COOLDOWNS.get(task_name, 3600)
                )
        
        # Load state
        state_data = state_store.load("periodic_state.json")
        self.load_state(state_data.get(self.state_key, {}))
    
    def load_state(self, state_data: Dict[str, Any]):
        """从持久化数据加载状态"""
        if not state_data:
            return
        
        cooldowns_data = state_data.get("cooldowns", {})
        for task_name, cd_data in cooldowns_data.items():
            if task_name in self.state.cooldowns:
                self.state.cooldowns[task_name].last_execute_ts = cd_data.get("last_execute_ts", 0)
                self.state.cooldowns[task_name].cooldown_seconds = cd_data.get("cooldown_seconds", 0)
                self.state.cooldowns[task_name].next_execute_ts = cd_data.get("next_execute_ts", 0)
        
        logger.info(f"[周期] 加载状态: {len(self.state.cooldowns)}个任务")
    
    def save_state(self) -> Dict[str, Any]:
        """保存状态到字典"""
        return {
            "cooldowns": {
                name: {
                    "last_execute_ts": cd.last_execute_ts,
                    "cooldown_seconds": cd.cooldown_seconds,
                    "next_execute_ts": cd.next_execute_ts,
                }
                for name, cd in self.state.cooldowns.items()
            }
        }
    
    def is_task_enabled(self, task_name: str) -> bool:
        """检查任务是否启用"""
        # 将任务名映射到配置键
        config_key_map = {
            "闭关修炼": "biguan",
            "引道": "yindao",
            "启阵": "qizhen",
            "问道": "wendao",
            "探寻裂缝": "rift_explore",
            "元婴出窍": "yuanying",
            "元婴状态": "yuanying",
        }
        
        config_key = config_key_map.get(task_name)
        if not config_key:
            return True  # 默认启用
        
        return self.enabled_tasks.get(config_key, True)
    
    def should_execute(self, task_name: str) -> bool:
        """检查任务是否应该执行"""
        if not self.is_task_enabled(task_name):
            return False
        
        if task_name not in self.state.cooldowns:
            return True
        
        cd = self.state.cooldowns[task_name]
        now = time.time()
        
        # 检查是否过了冷却时间
        return now >= cd.next_execute_ts
    
    def get_ready_tasks(self) -> list[tuple[str, int, int]]:
        """
        获取可以执行的任务
        
        Returns:
            列表of (command, priority, delay_seconds)
        """
        tasks = []
        now = time.time()
        delay_offset = 0  # Stagger commands to avoid slowmode
        
        for task_name, command in self.TASKS.items():
            if self.should_execute(task_name):
                # 任务优先级都是P1, 但要错开发送时间
                tasks.append((command, 1, delay_offset))
                logger.info(f"[周期] 任务就绪: {task_name}")
                delay_offset += 2  # 每个任务间隔2秒
        
        return tasks
    
    def parse_response(self, text: str, task_name: str) -> Optional[int]:
        """
        解析任务响应，提取冷却时间
        
        Args:
            text: 频道返回文本
            task_name: 任务名称
            
        Returns:
            冷却秒数
        """
        if not text or task_name not in self.state.cooldowns:
            return None
        
        cd = self.state.cooldowns[task_name]
        
        # 检查成功标识
        success_keywords = {
            "闭关修炼": ["闭关成功", "进入闭关"],
            "引道": ["你引动", "引道成功"],
            "启阵": ["启阵成功", "阵法运转"],
            "问道": ["问道", "天机"],
            "探寻裂缝": ["探寻成功", "遭遇风暴", "发现", "受创"],
            "元婴出窍": ["云游", "出窍成功", "元婴离体"],
            "元婴状态": ["元婴状态", "元神", "归窍", "出窍", "温养"],
        }
        
        keywords = success_keywords.get(task_name, [])
        is_success = any(kw in text for kw in keywords)
        
        if not is_success:
            # 检查是否在冷却中
            if "冷却" in text or "请在" in text or "后再" in text:
                cooldown = extract_cooldown_with_fallback(text, task_name)
                logger.info(f"[周期] {task_name}仍在冷却: {cooldown}秒")
                return cooldown
            
            logger.debug(f"[周期] {task_name}响应未识别: {text[:50]}")
            return None
        
        # 成功执行，提取冷却时间
        cooldown = extract_cooldown_with_fallback(text, task_name)
        
        # 更新状态
        now = time.time()
        cd.last_execute_ts = now
        cd.cooldown_seconds = cooldown
        cd.next_execute_ts = now + cooldown
        
        logger.info(f"[周期] {task_name}执行成功，冷却{cooldown}秒")
        
        # 对于探寻裂缝，如果失败（风暴/受创），安排预热
        if task_name == "探寻裂缝" and ("风暴" in text or "受创" in text):
            preheat_time = 5 * 60  # 提前5分钟
            logger.info(f"[周期] 探寻裂缝失败，将在冷却结束前{preheat_time}秒进行预热")
        
        return cooldown
    
    def mark_task_executed(self, task_name: str, cooldown_seconds: int = None):
        """标记任务已执行（手动调用）"""
        if task_name not in self.state.cooldowns:
            return
        
        cd = self.state.cooldowns[task_name]
        now = time.time()
        
        if cooldown_seconds is None:
            cooldown_seconds = cd.cooldown_seconds or PERIODIC_COOLDOWNS.get(task_name, 3600)
        
        cd.last_execute_ts = now
        cd.cooldown_seconds = cooldown_seconds
        cd.next_execute_ts = now + cooldown_seconds
        
        logger.info(f"[周期] 标记{task_name}已执行，下次执行时间: {cd.next_execute_ts}")
    
    async def start(self):
        """启动周期任务模块"""
        enabled_count = sum(1 for enabled in self.enabled_tasks.values() if enabled)
        if enabled_count == 0:
            logger.info("[周期] 所有周期任务均已禁用")
            return
        
        logger.info(f"[周期] 启动周期任务模块，已启用{enabled_count}个任务")
        
        # 调度就绪的任务
        for command, priority, delay in self.get_ready_tasks():
            await self.command_queue.enqueue(
                command,
                when=time.time() + delay,
                priority=priority,
                dedupe_key=f"periodic:{command}:{self.chat_id}"
            )
    
    async def handle_message(self, message) -> bool:
        """处理消息"""
        if not message.text:
            return False
        
        text = message.text
        
        # 尝试匹配任务响应
        for task_name in self.TASKS.keys():
            if any(kw in text for kw in [task_name, self.TASKS[task_name]]):
                cooldown = self.parse_response(text, task_name)
                if cooldown is not None:
                    # 保存状态
                    self._save_state()
                    
                    # 如果冷却时间很短，立即调度下一次执行
                    if cooldown < 3600:  # 小于1小时
                        await self.command_queue.enqueue(
                            self.TASKS[task_name],
                            when=time.time() + cooldown + 5,  # 加5秒缓冲
                            priority=1,
                            dedupe_key=f"periodic:{self.TASKS[task_name]}:{self.chat_id}"
                        )
                    
                    return True
        
        return False
    
    def _save_state(self):
        """保存状态到持久化存储"""
        state_data = self.state_store.load("periodic_state.json")
        state_data[self.state_key] = self.save_state()
        self.state_store.save("periodic_state.json", state_data)
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        status = {}
        for task_name, cd in self.state.cooldowns.items():
            if self.is_task_enabled(task_name):
                status[task_name] = {
                    "ready": self.should_execute(task_name),
                    "next_execute_ts": cd.next_execute_ts,
                    "cooldown_seconds": cd.cooldown_seconds
                }
        return status
