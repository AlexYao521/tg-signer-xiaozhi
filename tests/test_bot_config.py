"""
Tests for bot configuration
"""
import json
import tempfile
from pathlib import Path

import pytest

from tg_signer.bot_config import (
    BotConfig,
    DailyConfig,
    PeriodicConfig,
    StarObservationConfig,
    HerbGardenConfig,
    XiaozhiAIConfig,
    ActivityConfig,
    CommandResponseRule,
    create_default_bot_config,
    load_bot_config
)


def test_daily_config_defaults():
    """Test daily configuration defaults"""
    config = DailyConfig()
    assert config.enable_sign_in is True
    assert config.enable_transmission is True
    assert config.enable_greeting is False


def test_periodic_config_defaults():
    """Test periodic configuration defaults"""
    config = PeriodicConfig()
    assert config.enable_qizhen is True
    assert config.enable_zhuzhen is True
    assert config.enable_wendao is True
    assert config.enable_yindao is True
    assert config.enable_yuanying is True
    assert config.enable_rift_explore is True


def test_star_observation_config():
    """Test star observation configuration"""
    config = StarObservationConfig(
        enabled=True,
        default_star="天雷星",
        plate_count=5,
        sequence=["天雷星", "烈阳星"]
    )
    assert config.enabled is True
    assert config.default_star == "天雷星"
    assert config.plate_count == 5
    assert len(config.sequence) == 2


def test_xiaozhi_ai_config():
    """Test Xiaozhi AI configuration"""
    config = XiaozhiAIConfig(
        authorized_users=[123456, 789012],
        filter_keywords=["广告", "spam"],
        trigger_keywords=["@小智", "xiaozhi"]
    )
    assert 123456 in config.authorized_users
    assert "广告" in config.filter_keywords
    assert "@小智" in config.trigger_keywords


def test_command_response_rule():
    """Test command response rule"""
    rule = CommandResponseRule(
        pattern=r"问答\d+",
        response="这是回复",
        cooldown_seconds=300,
        priority=5
    )
    assert rule.pattern == r"问答\d+"
    assert rule.response == "这是回复"
    assert rule.cooldown_seconds == 300
    assert rule.enabled is True


def test_bot_config_creation():
    """Test bot configuration creation"""
    config = BotConfig(
        chat_id=-1001234567890,
        name="测试频道"
    )
    assert config.chat_id == -1001234567890
    assert config.name == "测试频道"
    assert isinstance(config.daily, DailyConfig)
    assert isinstance(config.periodic, PeriodicConfig)
    assert isinstance(config.star_observation, StarObservationConfig)
    assert isinstance(config.xiaozhi_ai, XiaozhiAIConfig)


def test_bot_config_with_custom_values():
    """Test bot configuration with custom values"""
    config = BotConfig(
        chat_id=-1001234567890,
        name="测试频道",
        daily=DailyConfig(
            enable_sign_in=False,
            enable_transmission=False,
            enable_greeting=True
        ),
        xiaozhi_ai=XiaozhiAIConfig(
            authorized_users=[12345]
        )
    )
    assert config.daily.enable_sign_in is False
    assert config.daily.enable_greeting is True
    assert config.xiaozhi_ai.authorized_users == [12345]


def test_create_default_bot_config():
    """Test creating default bot configuration"""
    config = create_default_bot_config(-1001234567890, "我的频道")
    assert config.chat_id == -1001234567890
    assert config.name == "我的频道"


def test_bot_config_json_serialization():
    """Test bot configuration JSON serialization"""
    config = BotConfig(
        chat_id=-1001234567890,
        name="测试频道",
        xiaozhi_ai=XiaozhiAIConfig(authorized_users=[12345])
    )
    
    # Serialize to dict
    config_dict = config.model_dump()
    assert config_dict["chat_id"] == -1001234567890
    assert config_dict["name"] == "测试频道"
    assert config_dict["xiaozhi_ai"]["authorized_users"] == [12345]
    
    # Deserialize from dict
    config2 = BotConfig(**config_dict)
    assert config2.chat_id == config.chat_id
    assert config2.name == config.name


def test_load_bot_config_from_file():
    """Test loading bot configuration from file"""
    config_data = {
        "chat_id": -1001234567890,
        "name": "测试频道",
        "daily": {
            "enable_sign_in": True,
            "enable_transmission": True,
            "enable_greeting": False
        },
        "xiaozhi_ai": {
            "authorized_users": [12345],
            "filter_keywords": ["spam"],
            "blacklist_users": [],
            "debug": False
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        temp_path = f.name
    
    try:
        config = load_bot_config(temp_path)
        assert config.chat_id == -1001234567890
        assert config.name == "测试频道"
        assert config.daily.enable_sign_in is True
        assert config.xiaozhi_ai.authorized_users == [12345]
    finally:
        Path(temp_path).unlink()


def test_bot_config_validation():
    """Test bot configuration validation"""
    # Valid config
    config = BotConfig(chat_id=-1001234567890)
    assert config.chat_id == -1001234567890
    
    # Invalid config (missing required field)
    with pytest.raises(Exception):
        BotConfig()


def test_custom_rules_in_bot_config():
    """Test custom rules in bot configuration"""
    rule1 = CommandResponseRule(
        pattern=r"测试\d+",
        response="测试回复"
    )
    rule2 = CommandResponseRule(
        pattern=r"问答.*",
        action="some_action",
        cooldown_seconds=600
    )
    
    config = BotConfig(
        chat_id=-1001234567890,
        custom_rules=[rule1, rule2]
    )
    
    assert len(config.custom_rules) == 2
    assert config.custom_rules[0].pattern == r"测试\d+"
    assert config.custom_rules[1].cooldown_seconds == 600
