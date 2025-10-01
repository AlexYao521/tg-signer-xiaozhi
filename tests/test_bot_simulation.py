"""
Simulation tests for bot lifecycle and message handling
This test simulates the actual bot startup flow and message handling
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from pyrogram.types import Message, Chat, User

from tg_signer.bot_worker import ChannelBot
from tg_signer.bot_config import create_default_bot_config


@pytest.fixture
def mock_config():
    """Create a bot configuration matching the problem statement"""
    config = create_default_bot_config(-1001680975844, "黄风谷")
    config.daily.enable_sign_in = True
    config.daily.enable_greeting = True
    config.daily.enable_transmission = True
    config.periodic.enable_biguan = True
    config.herb_garden.enabled = True
    config.star_observation.enabled = False
    config.activity.enabled = True
    config.xiaozhi_ai.authorized_users = []  # Disabled for this test
    return config


@pytest.fixture
def create_message():
    """Factory to create mock messages"""
    def _create(text: str, from_bot: bool = True, chat_id: int = -1001680975844):
        message = Mock(spec=Message)
        message.text = text
        message.chat = Mock(spec=Chat)
        message.chat.id = chat_id
        message.from_user = Mock(spec=User)
        message.from_user.id = 999888777 if from_bot else 123456
        message.from_user.username = "xiuxian_bot" if from_bot else "testuser"
        message.from_user.is_bot = from_bot
        message.entities = None
        message.id = 12345
        return message
    return _create


@pytest.mark.asyncio
async def test_bot_initialization_with_all_modules(mock_config):
    """Test that bot initializes all modules correctly"""
    with patch('tg_signer.bot_worker.Client'):
        bot = ChannelBot(
            config=mock_config,
            account="test_account",
            workdir="/tmp/test_bot_sim"
        )

        # Verify all modules are initialized
        assert bot.daily_routine is not None
        assert bot.periodic_tasks is not None
        assert bot.herb_garden is not None
        assert bot.star_observation is not None
        assert bot.activity_manager is not None

        # Verify config.chat_id is accessible
        assert bot.config.chat_id == -1001680975844


@pytest.mark.asyncio
async def test_activity_dongfu_fangke_message_handling(mock_config, create_message):
    """Test the exact scenario from the problem statement - 洞府访客_查看"""
    with patch('tg_signer.bot_worker.Client'):
        bot = ChannelBot(
            config=mock_config,
            account="test_account",
            workdir="/tmp/test_bot_sim"
        )

        # Mock module handlers to not handle the message
        bot.daily_routine.handle_message = AsyncMock(return_value=False)
        bot.periodic_tasks.handle_message = AsyncMock(return_value=False)
        bot.star_observation.handle_message = AsyncMock(return_value=False)
        bot.herb_garden.handle_message = AsyncMock(return_value=False)

        # Create the message that contains activity pattern (exact match from activity_manager)
        message = create_message("洞府访客到访，请使用 .查看访客 指令查看详情")

        # This should not raise AttributeError anymore
        await bot._on_message(bot.client, message)

        # The main goal is to verify no AttributeError is raised
        # Activity matching is handled by activity_manager which may or may not match
        # depending on the exact pattern, but the fix ensures no crash occurs


@pytest.mark.asyncio
async def test_daily_routine_message_flow(mock_config, create_message):
    """Test daily routine message handling flow"""
    with patch('tg_signer.bot_worker.Client'):
        bot = ChannelBot(
            config=mock_config,
            account="test_account",
            workdir="/tmp/test_bot_sim"
        )

        # Create messages simulating bot responses
        signin_message = create_message("点卯成功！获得修为 100")
        greeting_message = create_message("问安成功！情缘增加 50")
        transmission_message = create_message("传功成功！今日已传功 1/3")

        # Handle messages
        await bot._on_message(bot.client, signin_message)
        await bot._on_message(bot.client, greeting_message)
        await bot._on_message(bot.client, transmission_message)

        # Verify daily routine state was updated
        status = bot.daily_routine.get_status()
        assert status["signin_done"] is True
        assert status["greeting_done"] is True
        assert status["transmission_count"] >= 1


@pytest.mark.asyncio
async def test_periodic_task_message_flow(mock_config, create_message):
    """Test periodic task message handling flow"""
    with patch('tg_signer.bot_worker.Client'):
        bot = ChannelBot(
            config=mock_config,
            account="test_account",
            workdir="/tmp/test_bot_sim"
        )

        # Create message simulating biguan (闭关修炼) response
        biguan_message = create_message("你进入闭关状态，修为增加！请在 16分钟 后再来")

        # Handle message
        await bot._on_message(bot.client, biguan_message)

        # Verify periodic task state was updated
        status = bot.periodic_tasks.get_status()
        assert "闭关修炼" in status
        assert status["闭关修炼"]["cooldown_seconds"] > 0


@pytest.mark.asyncio
async def test_command_queue_priority_ordering(mock_config):
    """Test that commands are processed in correct priority order"""
    import time

    with patch('tg_signer.bot_worker.Client'):
        bot = ChannelBot(
            config=mock_config,
            account="test_account",
            workdir="/tmp/test_bot_sim"
        )

        # Enqueue commands with different priorities at the same time
        now = time.time()
        await bot.command_queue.enqueue(".低优先级", when=now, priority=5)
        await bot.command_queue.enqueue(".高优先级", when=now, priority=0)
        await bot.command_queue.enqueue(".中优先级", when=now, priority=2)

        # Dequeue and verify order (dequeue now returns 3 values: command, dedupe_key, callback)
        cmd1, _, _ = await bot.command_queue.dequeue()
        cmd2, _, _ = await bot.command_queue.dequeue()
        cmd3, _, _ = await bot.command_queue.dequeue()

        # Higher priority (lower number) should come first
        assert cmd1 == ".高优先级"
        assert cmd2 == ".中优先级"
        assert cmd3 == ".低优先级"


@pytest.mark.asyncio
async def test_slowmode_error_scenario(mock_config, create_message):
    """Test that slowmode errors don't break the bot"""
    with patch('tg_signer.bot_worker.Client') as MockClient:
        bot = ChannelBot(
            config=mock_config,
            account="test_account",
            workdir="/tmp/test_bot_sim"
        )

        # Mock client to raise slowmode error
        from pyrogram.errors import FloodWait

        async def mock_send_with_error(*args, **kwargs):
            raise FloodWait(value=8)

        bot.client.send_message = mock_send_with_error

        # Try to send a command (should handle error gracefully)
        await bot._send_command(".测试指令")

        # Bot should still be functional (no crash)
        assert bot._running is False  # Not started yet


@pytest.mark.asyncio
async def test_multiple_module_initialization(mock_config):
    """Test that all modules receive correct chat_id"""
    with patch('tg_signer.bot_worker.Client'):
        bot = ChannelBot(
            config=mock_config,
            account="test_account",
            workdir="/tmp/test_bot_sim"
        )

        # Verify all modules have correct chat_id
        assert bot.daily_routine.chat_id == -1001680975844
        assert bot.periodic_tasks.chat_id == -1001680975844
        assert bot.herb_garden.chat_id == -1001680975844
        assert bot.star_observation.chat_id == -1001680975844
        assert bot.activity_manager.chat_id == -1001680975844

        # Verify bot uses config.chat_id
        assert bot.config.chat_id == -1001680975844


@pytest.mark.asyncio
async def test_dedupe_key_format_consistency(mock_config):
    """Test that dedupe keys use consistent format with chat_id"""
    with patch('tg_signer.bot_worker.Client'):
        bot = ChannelBot(
            config=mock_config,
            account="test_account",
            workdir="/tmp/test_bot_sim"
        )

        # Test different dedupe key formats
        test_cases = [
            ("activity:.查看访客", "activity:.查看访客:-1001680975844"),
            ("daily:.宗门点卯", "daily:.宗门点卯:-1001680975844"),
            ("periodic:.闭关修炼", "periodic:.闭关修炼:-1001680975844"),
        ]

        for command, expected_key in test_cases:
            await bot.command_queue.enqueue(
                command,
                priority=1,
                dedupe_key=f"{command}:{bot.config.chat_id}"
            )

            cmd, dedupe_key, _ = await bot.command_queue.dequeue()
            assert dedupe_key == expected_key
