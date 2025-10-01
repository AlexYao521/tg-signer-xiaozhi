"""
Tests for Xiaozhi AI client
"""
import pytest

from tg_signer.xiaozhi_client import (
    XiaozhiClient,
    XiaozhiMessage,
    create_xiaozhi_client
)


def test_xiaozhi_message():
    """Test Xiaozhi message dataclass"""
    msg = XiaozhiMessage(
        text="Hello",
        is_final=True,
        session_id="test123",
        timestamp=1234567890.0
    )
    assert msg.text == "Hello"
    assert msg.is_final is True
    assert msg.session_id == "test123"
    assert msg.timestamp == 1234567890.0


def test_xiaozhi_client_creation():
    """Test Xiaozhi client creation"""
    client = XiaozhiClient(
        websocket_url="wss://test.example.com",
        access_token="test-token",
        auto_reconnect=True,
        max_reconnect_attempts=5
    )
    assert client.websocket_url == "wss://test.example.com"
    assert client.access_token == "test-token"
    assert client.auto_reconnect is True
    assert client.max_reconnect_attempts == 5


@pytest.mark.asyncio
async def test_xiaozhi_client_send_message():
    """Test sending message to Xiaozhi AI"""
    client = XiaozhiClient(
        websocket_url="wss://test.example.com",
        access_token="test-token"
    )
    
    # For now, this returns a placeholder response
    response = await client.send_message("Hello")
    assert "Hello" in response


def test_create_xiaozhi_client_with_config():
    """Test creating Xiaozhi client from configuration"""
    config = {
        "SYSTEM_OPTIONS": {
            "NETWORK": {
                "WEBSOCKET_URL": "wss://api.tenclass.net/xiaozhi/v1/",
                "WEBSOCKET_ACCESS_TOKEN": "test-token"
            }
        },
        "TG_SIGNER": {
            "XIAOZHI_AI": {
                "enabled": True,
                "protocol_type": "websocket",
                "auto_reconnect": True,
                "max_reconnect_attempts": 5
            }
        }
    }
    
    client = create_xiaozhi_client(config)
    assert client is not None
    assert client.websocket_url == "wss://api.tenclass.net/xiaozhi/v1/"
    assert client.access_token == "test-token"
    assert client.auto_reconnect is True


def test_create_xiaozhi_client_disabled():
    """Test creating Xiaozhi client when disabled"""
    config = {
        "SYSTEM_OPTIONS": {
            "NETWORK": {
                "WEBSOCKET_URL": "wss://api.tenclass.net/xiaozhi/v1/",
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


def test_create_xiaozhi_client_missing_config():
    """Test creating Xiaozhi client with missing configuration"""
    config = {
        "SYSTEM_OPTIONS": {
            "NETWORK": {}
        },
        "TG_SIGNER": {
            "XIAOZHI_AI": {
                "enabled": True
            }
        }
    }
    
    client = create_xiaozhi_client(config)
    assert client is None
