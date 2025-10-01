"""
冷却配置常量 (Cooldown Configuration Constants)
根据需求文档定义的冷却时间规则
"""

# 每日任务冷却时间 (Daily Tasks Cooldown)
DAILY_COOLDOWNS = {
    "宗门点卯": 24 * 3600,  # 24小时，过凌晨自动执行
    "宗门传功": 24 * 3600,  # 24小时，最多3次
    "每日问安": 24 * 3600,  # 24小时
}

# 周期任务冷却时间 (Periodic Tasks Cooldown)
PERIODIC_COOLDOWNS = {
    "闭关修炼": 16 * 60,  # 16分钟（兜底）
    "引道": 12 * 3600,  # 12小时
    "启阵": 12 * 3600,  # 12小时  
    "探寻裂缝": 12 * 3600,  # 12小时
    "问道": 12 * 3600,  # 12小时
    "元婴出窍": 8 * 3600,  # 8小时
}

# 星宫牵引冷却时间 (Star Palace Pull Cooldown)
STAR_PULL_COOLDOWNS = {
    "赤血星": 4 * 3600,  # 4小时
    "庚金星": 6 * 3600,  # 6小时
    "建木星": 8 * 3600,  # 8小时
    "天雷星": 24 * 3600,  # 24小时
    "帝魂星": 48 * 3600,  # 48小时
}

# 小药园冷却时间 (Herb Garden Cooldown)
HERB_GARDEN_COOLDOWNS = {
    "灵树灌溉": 1 * 3600,  # 1小时
}

# 小药园种子成熟时间 (Herb Garden Seed Maturity Time)
SEED_MATURITY_HOURS = {
    "凝血草种子": 4,  # 4小时
    "清灵草种子": 8,  # 8小时
}

# 冷却解析的最小阈值（秒）- 低于此值视为解析异常
MIN_COOLDOWN_THRESHOLD = 600  # 10分钟

# 默认兜底冷却时间（秒）- 当解析失败时使用
DEFAULT_COOLDOWN_FALLBACK = {
    "闭关修炼": 16 * 60,
    "引道": 12 * 3600,
    "启阵": 12 * 3600,
    "探寻裂缝": 12 * 3600,
    "问道": 12 * 3600,
    "元婴出窍": 8 * 3600,
    "default": 30 * 60,  # 默认30分钟
}


def get_default_cooldown(command: str) -> int:
    """
    获取指令的默认冷却时间（秒）
    
    Args:
        command: 指令名称，如 "闭关修炼", "引道" 等
        
    Returns:
        冷却时间（秒）
    """
    # 先从每日任务查找
    if command in DAILY_COOLDOWNS:
        return DAILY_COOLDOWNS[command]
    
    # 再从周期任务查找
    if command in PERIODIC_COOLDOWNS:
        return PERIODIC_COOLDOWNS[command]
    
    # 小药园任务
    if command in HERB_GARDEN_COOLDOWNS:
        return HERB_GARDEN_COOLDOWNS[command]
    
    # 从回退字典查找
    if command in DEFAULT_COOLDOWN_FALLBACK:
        return DEFAULT_COOLDOWN_FALLBACK[command]
    
    # 返回通用默认值
    return DEFAULT_COOLDOWN_FALLBACK["default"]


def get_star_pull_cooldown(star_name: str) -> int:
    """
    获取星宫牵引指定星辰的冷却时间
    
    Args:
        star_name: 星辰名称，如 "赤血星", "庚金星" 等
        
    Returns:
        冷却时间（秒）
    """
    return STAR_PULL_COOLDOWNS.get(star_name, 12 * 3600)  # 默认12小时


def get_seed_maturity_hours(seed_name: str) -> int:
    """
    获取种子成熟所需小时数
    
    Args:
        seed_name: 种子名称，如 "凝血草种子"
        
    Returns:
        成熟所需小时数
    """
    return SEED_MATURITY_HOURS.get(seed_name, 8)  # 默认8小时
