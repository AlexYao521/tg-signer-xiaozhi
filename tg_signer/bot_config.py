"""
Channel Automation Bot Configuration
Based on ARCHITECTURE.md design specifications
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DailyConfig(BaseModel):
    """Daily routine configuration"""
    enable_sign_in: bool = True
    enable_transmission: bool = True
    enable_greeting: bool = False


class PeriodicConfig(BaseModel):
    """Periodic tasks configuration"""
    enable_biguan: bool = True  # 闭关修炼
    enable_qizhen: bool = True  # 启阵
    enable_zhuzhen: bool = True  # 助阵
    enable_wendao: bool = True  # 问道
    enable_yindao: bool = True  # 引道
    enable_yuanying: bool = True  # 元婴
    enable_rift_explore: bool = True  # 裂缝探索


class StarObservationConfig(BaseModel):
    """Star observation configuration"""
    enabled: bool = True
    default_star: str = "天雷星"
    plate_count: int = 5
    sequence: List[str] = Field(default_factory=lambda: ["天雷星", "烈阳星", "玄冰星"])


class SeedConfig(BaseModel):
    """Seed configuration for herb garden"""
    maturity_hours: int
    exchange_batch: int
    exchange_command: str


class HerbGardenConfig(BaseModel):
    """Herb garden automation configuration"""
    enabled: bool = False
    default_seed: str = "凝血草种子"
    seeds: Dict[str, SeedConfig] = Field(default_factory=dict)
    scan_interval_min: int = 900  # seconds
    post_maintenance_rescan: int = 30  # seconds
    post_harvest_rescan: int = 20  # seconds
    seed_shortage_retry: int = 600  # seconds


class XiaozhiAIConfig(BaseModel):
    """Xiaozhi AI configuration"""
    authorized_users: List[int] = Field(default_factory=list)
    filter_keywords: List[str] = Field(default_factory=list)
    blacklist_users: List[int] = Field(default_factory=list)
    trigger_keywords: List[str] = Field(default_factory=lambda: ["@小智", "小智AI", "xiaozhi"])
    response_prefix: str = "小智AI回复: "
    debug: bool = False


class ActivityConfig(BaseModel):
    """Activity recognition and response configuration"""
    enabled: bool = True
    rules_extra: List[Dict[str, Any]] = Field(default_factory=list)


class CommandResponseRule(BaseModel):
    """
    Flexible command-response mapping rule.
    Allows DSL-style configuration without code changes.
    """
    pattern: str  # Regex pattern to match
    response: Optional[str] = None  # Optional response text
    action: Optional[str] = None  # Optional action to execute
    cooldown_seconds: int = 0  # Cooldown period
    priority: int = 5  # Priority (lower = higher priority)
    enabled: bool = True


class BotConfig(BaseModel):
    """
    Main bot configuration for a channel/sect.
    Follows ARCHITECTURE.md sect_a.json structure.
    """
    chat_id: int
    name: Optional[str] = None
    
    # Feature toggles
    daily: DailyConfig = Field(default_factory=DailyConfig)
    periodic: PeriodicConfig = Field(default_factory=PeriodicConfig)
    star_observation: StarObservationConfig = Field(default_factory=StarObservationConfig)
    herb_garden: HerbGardenConfig = Field(default_factory=HerbGardenConfig)
    xiaozhi_ai: XiaozhiAIConfig = Field(default_factory=XiaozhiAIConfig)
    activity: ActivityConfig = Field(default_factory=ActivityConfig)
    
    # Flexible command-response rules
    custom_rules: List[CommandResponseRule] = Field(default_factory=list)
    
    # Timing configuration
    sign_interval: float = 10.0  # seconds between commands (minimum 10s for channel messages)
    min_send_interval: float = 10.0  # minimum interval between any sends (10s minimum + boundary)
    
    class Config:
        json_schema_extra = {
            "example": {
                "chat_id": -1001234567890,
                "name": "仙门频道",
                "daily": {
                    "enable_sign_in": True,
                    "enable_transmission": True,
                    "enable_greeting": False
                },
                "periodic": {
                    "enable_biguan": True,
                    "enable_qizhen": True,
                    "enable_zhuzhen": True,
                    "enable_wendao": True,
                    "enable_yindao": True,
                    "enable_yuanying": True,
                    "enable_rift_explore": True
                },
                "star_observation": {
                    "enabled": True,
                    "default_star": "天雷星",
                    "plate_count": 5,
                    "sequence": ["天雷星", "烈阳星", "玄冰星"]
                },
                "xiaozhi_ai": {
                    "authorized_users": [12345678],
                    "filter_keywords": ["广告", "刷屏"],
                    "blacklist_users": [],
                    "debug": False
                },
                "activity": {
                    "enabled": True,
                    "rules_extra": []
                }
            }
        }


def load_bot_config(config_path: str) -> BotConfig:
    """Load bot configuration from JSON file"""
    import json
    with open(config_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return BotConfig(**data)


def create_default_bot_config(chat_id: int, name: Optional[str] = None) -> BotConfig:
    """Create a default bot configuration"""
    return BotConfig(
        chat_id=chat_id,
        name=name or f"频道_{chat_id}"
    )
