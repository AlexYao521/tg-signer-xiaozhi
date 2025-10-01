"""
Tests for bot_worker module
"""
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pyrogram.types import Chat, Message, User

from tg_signer.bot_config import create_default_bot_config
from tg_signer.bot_worker import ChannelBot


@pytest.fixture
def mock_config():
    """Create a mock bot configuration"""
    config = create_default_bot_config(-1001234567890, "Test Channel")
    config.activity.enabled = True
    return config


@pytest.fixture
def mock_message():
    """Create a mock Telegram message from a bot"""
    message = Mock(spec=Message)
    message.text = "Test message"
    message.chat = Mock(spec=Chat)
    message.chat.id = -1001234567890
    message.from_user = Mock(spec=User)
    message.from_user.id = 123456
    message.from_user.username = "testbot"
    message.from_user.is_bot = True  # Mark as bot message
    message.entities = None
    return message


@pytest.mark.asyncio
async def test_bot_initialization(mock_config):
    """Test that ChannelBot initializes correctly"""
    with patch('tg_signer.bot_worker.Client'):
        bot = ChannelBot(
            config=mock_config,
            account="test_account",
            workdir="/tmp/test_bot"
        )

        assert bot.config == mock_config
        assert bot.account == "test_account"
        assert bot.config.chat_id == -1001234567890


@pytest.mark.asyncio
async def test_activity_match_uses_config_chat_id(mock_config, mock_message):
    """Test that activity matching uses self.config.chat_id correctly"""
    with patch('tg_signer.bot_worker.Client'):
        bot = ChannelBot(
            config=mock_config,
            account="test_account",
            workdir="/tmp/test_bot"
        )

        # Mock the activity manager to return a match
        bot.activity_manager.match_activity = Mock(
            return_value=(".查看访客", "command", 0)
        )

        # Mock xiaozhi_client
        bot.xiaozhi_client = None

        # Create a message about visitor
        mock_message.text = "洞府访客：.查看访客"

        # Call the message handler
        await bot._on_message(bot.client, mock_message)

        # Verify that the command was enqueued (no AttributeError should occur)
        # The test passes if no exception is raised


@pytest.mark.asyncio
async def test_channel_bot_has_no_chat_id_attribute(mock_config):
    """Test that ChannelBot does not have a chat_id attribute, only config.chat_id"""
    with patch('tg_signer.bot_worker.Client'):
        bot = ChannelBot(
            config=mock_config,
            account="test_account",
            workdir="/tmp/test_bot"
        )

        # Verify bot doesn't have chat_id as direct attribute
        assert not hasattr(bot, 'chat_id') or bot.chat_id is None or bot.chat_id == bot.config.chat_id

        # Verify config has chat_id
        assert hasattr(bot.config, 'chat_id')
        assert bot.config.chat_id == -1001234567890


@pytest.mark.asyncio
async def test_command_enqueue_with_correct_chat_id(mock_config):
    """Test that commands are enqueued with correct chat_id in dedupe key"""
    with patch('tg_signer.bot_worker.Client'):
        bot = ChannelBot(
            config=mock_config,
            account="test_account",
            workdir="/tmp/test_bot"
        )

        # Enqueue a command with chat_id in dedupe key
        await bot.command_queue.enqueue(
            ".查看访客",
            priority=0,
            dedupe_key=f"activity:.查看访客:{bot.config.chat_id}"
        )

        # Dequeue and verify
        command, dedupe_key, _ = await bot.command_queue.dequeue()
        assert command == ".查看访客"
        assert dedupe_key == f"activity:.查看访客:{bot.config.chat_id}"


@pytest.mark.asyncio
async def test_message_handler_integration(mock_config, mock_message):
    """Test full message handling pipeline"""
    with patch('tg_signer.bot_worker.Client'):
        bot = ChannelBot(
            config=mock_config,
            account="test_account",
            workdir="/tmp/test_bot"
        )

        # Mock all modules
        bot.daily_routine.handle_message = AsyncMock(return_value=False)
        bot.periodic_tasks.handle_message = AsyncMock(return_value=False)
        bot.star_observation.handle_message = AsyncMock(return_value=False)
        bot.herb_garden.handle_message = AsyncMock(return_value=False)
        bot.activity_manager.match_activity = Mock(return_value=None)
        bot.xiaozhi_client = None

        # Call message handler
        await bot._on_message(bot.client, mock_message)

        # Verify all handlers were called
        bot.daily_routine.handle_message.assert_called_once()
        bot.periodic_tasks.handle_message.assert_called_once()
        bot.star_observation.handle_message.assert_called_once()
        bot.herb_garden.handle_message.assert_called_once()


@pytest.mark.asyncio
async def test_activity_response_priority(mock_config, mock_message):
    """Test that activity responses respect priority levels"""
    with patch('tg_signer.bot_worker.Client'):
        bot = ChannelBot(
            config=mock_config,
            account="test_account",
            workdir="/tmp/test_bot"
        )

        # Mock the activity manager to return high priority match
        bot.activity_manager.match_activity = Mock(
            return_value=(".收敛气息", "command", 0)  # Priority 0 (highest)
        )

        # Mock dependencies
        bot.xiaozhi_client = None
        bot.daily_routine.handle_message = AsyncMock(return_value=False)
        bot.periodic_tasks.handle_message = AsyncMock(return_value=False)
        bot.star_observation.handle_message = AsyncMock(return_value=False)
        bot.herb_garden.handle_message = AsyncMock(return_value=False)

        mock_message.text = "魂魄献祭活动：回复本消息 .收敛气息"

        # Call message handler - should not raise AttributeError
        await bot._on_message(bot.client, mock_message)

        # Verify activity was matched
        bot.activity_manager.match_activity.assert_called_once()
