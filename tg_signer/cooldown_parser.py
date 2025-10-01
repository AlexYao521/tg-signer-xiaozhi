"""
冷却时间解析工具 (Cooldown Parser Utility)
统一解析频道返回的冷却时间文本
"""
import re
import logging
from typing import Optional

from .cooldown_config import MIN_COOLDOWN_THRESHOLD, get_default_cooldown

logger = logging.getLogger("tg-signer.cooldown")


def _extract_cooldown_seconds(text: str, command: str = None) -> Optional[int]:
    """
    从文本中提取冷却时间（秒）
    
    支持格式：
    - "X小时Y分钟Z秒"
    - "Y分钟Z秒"
    - "Z秒"
    - "X小时"
    
    Args:
        text: 包含冷却时间的文本
        command: 指令名称，用于回退到默认冷却时间
        
    Returns:
        冷却秒数，解析失败返回 None
        
    Examples:
        >>> _extract_cooldown_seconds("请在 12小时30分钟 后再来")
        45000
        >>> _extract_cooldown_seconds("需要 3分钟20秒 方可再次使用")
        200
        >>> _extract_cooldown_seconds("冷却中，剩余 45秒")
        45
    """
    if not text:
        return None
    
    # 标准化文本：处理全角字符和空格
    text = text.replace("　", " ")  # 全角空格转半角
    text = re.sub(r'\s+', ' ', text)  # 多个空格合并为一个
    
    # 冷却时间提取正则表达式
    # 支持 "X小时Y分钟Z秒" / "Y分钟Z秒" / "Z秒" / "X小时" 等组合
    # 使用单个正则表达式匹配整个时间段
    pattern = r'(\d+)\s*(?:小时|时)|(\d+)\s*(?:分钟|分)|(\d+)\s*秒'
    
    matches = re.findall(pattern, text)
    
    if not matches:
        logger.debug(f"[冷却解析] 未找到匹配的冷却时间格式: {text}")
        return None
    
    total_seconds = 0
    parsed_any = False
    
    # 遍历所有匹配项
    for match in matches:
        hours, minutes, seconds = match
        
        if hours:
            total_seconds += int(hours) * 3600
            parsed_any = True
        if minutes:
            total_seconds += int(minutes) * 60
            parsed_any = True
        if seconds:
            total_seconds += int(seconds)
            parsed_any = True
    
    if not parsed_any:
        logger.debug(f"[冷却解析] 未能解析出有效数值: {text}")
        return None
    
    # 检查解析结果是否合理
    # 如果解析出的时间太短（小于阈值），可能是解析错误
    if total_seconds < MIN_COOLDOWN_THRESHOLD and command:
        default_cd = get_default_cooldown(command)
        if default_cd > 3600:  # 如果默认冷却时间大于1小时
            logger.warning(
                f"[冷却解析] 解析结果 {total_seconds}秒 低于阈值 {MIN_COOLDOWN_THRESHOLD}秒，"
                f"指令 '{command}' 默认冷却为 {default_cd}秒，使用默认值"
            )
            return None
    
    logger.info(f"[冷却解析] 成功解析: {text} -> {total_seconds}秒")
    return total_seconds


def extract_cooldown_with_fallback(text: str, command: str) -> int:
    """
    从文本中提取冷却时间，失败时使用默认值
    
    Args:
        text: 包含冷却时间的文本
        command: 指令名称
        
    Returns:
        冷却秒数（保证返回有效值）
    """
    cooldown = _extract_cooldown_seconds(text, command)
    
    if cooldown is None:
        default_cd = get_default_cooldown(command)
        logger.warning(
            f"[冷却解析] 解析失败，使用默认冷却: {command} -> {default_cd}秒"
        )
        return default_cd
    
    return cooldown


def parse_time_remaining(text: str) -> Optional[int]:
    """
    解析剩余时间文本（用于成长中的灵田、凝聚中的星辰等）
    
    Args:
        text: 包含剩余时间的文本，如 "剩余: 17分钟12秒"
        
    Returns:
        剩余秒数
    """
    return _extract_cooldown_seconds(text)


def format_cooldown(seconds: int) -> str:
    """
    将秒数格式化为人类可读的时间字符串
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化的时间字符串，如 "12小时30分钟"
    """
    if seconds < 60:
        return f"{seconds}秒"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0:
        parts.append(f"{minutes}分钟")
    if secs > 0 or not parts:  # 如果没有其他部分，至少显示秒
        parts.append(f"{secs}秒")
    
    return "".join(parts)
