"""
Integration tests for the bot system
"""
import json
import tempfile
from pathlib import Path

from tg_signer.bot_config import BotConfig, create_default_bot_config
from tg_signer.bot_worker import StateStore, CommandQueue
from tg_signer.xiaozhi_client import create_xiaozhi_client


def test_state_store_operations():
    """Test state store save and load"""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = StateStore(tmpdir)
        
        # Save state
        data = {"key1": "value1", "key2": 123}
        store.save("test.json", data)
        
        # Load state
        loaded = store.load("test.json")
        assert loaded == data
        
        # Load non-existent file
        empty = store.load("nonexistent.json")
        assert empty == {}


def test_command_queue_basic():
    """Test basic command queue operations"""
    import asyncio
    import time
    
    async def test():
        queue = CommandQueue()
        
        # Enqueue commands with explicit timestamps to control order
        now = time.time()
        await queue.enqueue("command1", when=now, priority=1)
        await queue.enqueue("command2", when=now, priority=2)
        await queue.enqueue("command3", when=now, priority=1)
        
        # Dequeue commands
        results = []
        for _ in range(3):
            cmd, _ = await queue.dequeue()
            results.append(cmd)
        
        # Both priority 1 commands should come before priority 2
        # The exact order within same priority depends on insertion order
        priority_1_commands = [cmd for cmd in results if cmd in ["command1", "command3"]]
        priority_2_commands = [cmd for cmd in results if cmd == "command2"]
        
        assert len(priority_1_commands) == 2, f"Should have 2 priority 1 commands, got {priority_1_commands}"
        assert len(priority_2_commands) == 1, f"Should have 1 priority 2 command, got {priority_2_commands}"
        
        # Priority 1 commands should come first
        assert results.index("command1") < results.index("command2")
        assert results.index("command3") < results.index("command2")
        
        assert queue.empty()
    
    asyncio.run(test())


def test_command_queue_deduplication():
    """Test command queue deduplication"""
    import asyncio
    
    async def test():
        queue = CommandQueue()
        
        # Enqueue with dedupe key
        await queue.enqueue("command1", dedupe_key="key1")
        await queue.enqueue("command1", dedupe_key="key1")  # Should be ignored
        await queue.enqueue("command2", dedupe_key="key2")
        
        # Should only have 2 commands
        cmd1, _ = await queue.dequeue()
        cmd2, _ = await queue.dequeue()
        
        assert queue.empty()
    
    asyncio.run(test())


def test_bot_config_full_workflow():
    """Test full bot configuration workflow"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / "bot_configs"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "test_bot.json"
        
        # Create config
        config = create_default_bot_config(-1001234567890, "测试频道")
        config.daily.enable_sign_in = True
        config.xiaozhi_ai.authorized_users = [123456]
        
        # Save config
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config.model_dump(), f, indent=2)
        
        # Load config
        with open(config_file, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
        loaded_config = BotConfig(**loaded_data)
        
        # Verify
        assert loaded_config.chat_id == config.chat_id
        assert loaded_config.name == config.name
        assert loaded_config.daily.enable_sign_in is True
        assert loaded_config.xiaozhi_ai.authorized_users == [123456]


def test_xiaozhi_client_creation_with_config():
    """Test creating Xiaozhi client from config"""
    config = {
        "SYSTEM_OPTIONS": {
            "NETWORK": {
                "WEBSOCKET_URL": "wss://test.example.com",
                "WEBSOCKET_ACCESS_TOKEN": "test-token"
            }
        },
        "TG_SIGNER": {
            "XIAOZHI_AI": {
                "enabled": True,
                "protocol_type": "websocket"
            }
        }
    }
    
    client = create_xiaozhi_client(config)
    assert client is not None
    assert client.websocket_url == "wss://test.example.com"
    assert client.access_token == "test-token"


def test_xiaozhi_client_disabled():
    """Test Xiaozhi client when disabled"""
    config = {
        "SYSTEM_OPTIONS": {
            "NETWORK": {
                "WEBSOCKET_URL": "wss://test.example.com",
                "WEBSOCKET_ACCESS_TOKEN": "test-token"
            }
        },
        "TG_SIGNER": {
            "XIAOZHI_AI": {
                "enabled": False
            }
        }
    }
    
    client = create_xiaozhi_client(config)
    assert client is None


def test_bot_config_validation():
    """Test bot configuration validation"""
    # Valid config
    config_data = {
        "chat_id": -1001234567890,
        "name": "Test"
    }
    config = BotConfig(**config_data)
    assert config.chat_id == -1001234567890
    
    # Check defaults are applied
    assert config.daily.enable_sign_in is True
    assert config.periodic.enable_qizhen is True
    assert config.star_observation.enabled is True


def test_example_bot_config_valid():
    """Test that example_bot_config.json is valid"""
    config_path = Path(__file__).parent.parent / "example_bot_config.json"
    
    if not config_path.exists():
        # Skip if example file doesn't exist
        return
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
    
    # Should not raise exception
    config = BotConfig(**config_data)
    assert config.chat_id == -1001234567890
    assert config.name == "仙门频道示例"
