"""
Tests for enhanced CommandQueue features:
- State tracking (pending/executing/completed/failed)
- Callback support
- Priority-based execution
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from tg_signer.bot_worker import CommandQueue, ChannelBot
from tg_signer.bot_config import create_default_bot_config


@pytest.mark.asyncio
async def test_command_queue_state_tracking():
    """Test command state tracking throughout execution lifecycle"""
    queue = CommandQueue()
    
    # Enqueue a command with dedupe key
    dedupe_key = "test:command:123"
    await queue.enqueue(
        ".test command",
        priority=1,
        dedupe_key=dedupe_key
    )
    
    # Initial state should be pending
    assert queue.get_state(dedupe_key) == "pending"
    
    # Dequeue the command (state changes to executing)
    cmd, key, callback = await queue.dequeue()
    assert cmd == ".test command"
    assert key == dedupe_key
    assert queue.get_state(dedupe_key) == "executing"
    
    # Mark as completed
    queue.mark_completed(dedupe_key, success=True)
    assert queue.get_state(dedupe_key) == "completed"
    
    # Dedupe key should be removed from pending
    assert dedupe_key not in queue._pending


@pytest.mark.asyncio
async def test_command_queue_callback_execution():
    """Test callback execution after command completion"""
    queue = CommandQueue()
    
    # Create a callback tracker
    callback_executed = asyncio.Event()
    callback_data = {}
    
    async def test_callback():
        callback_data["executed"] = True
        callback_executed.set()
    
    # Enqueue with callback
    await queue.enqueue(
        ".test command",
        priority=1,
        dedupe_key="test:callback:456",
        callback=test_callback
    )
    
    # Dequeue
    cmd, key, callback = await queue.dequeue()
    assert callback is not None
    
    # Execute callback
    await callback()
    await callback_executed.wait()
    
    # Verify callback was executed
    assert callback_data.get("executed") is True


@pytest.mark.asyncio
async def test_command_queue_failed_state():
    """Test marking command as failed"""
    queue = CommandQueue()
    
    dedupe_key = "test:fail:789"
    await queue.enqueue(
        ".failing command",
        priority=1,
        dedupe_key=dedupe_key
    )
    
    # Dequeue
    cmd, key, _ = await queue.dequeue()
    
    # Mark as failed
    queue.mark_completed(dedupe_key, success=False)
    assert queue.get_state(dedupe_key) == "failed"


@pytest.mark.asyncio
async def test_command_queue_priority_levels():
    """Test all priority levels (P0-P3)"""
    queue = CommandQueue()
    
    # Enqueue commands with all priority levels at the same time
    import time
    now = time.time()
    await queue.enqueue(".P3低优先级", when=now, priority=3)
    await queue.enqueue(".P0立即", when=now, priority=0)
    await queue.enqueue(".P2正常", when=now, priority=2)
    await queue.enqueue(".P1高", when=now, priority=1)
    
    # Dequeue and verify order: P0, P1, P2, P3
    cmd1, _, _ = await queue.dequeue()
    cmd2, _, _ = await queue.dequeue()
    cmd3, _, _ = await queue.dequeue()
    cmd4, _, _ = await queue.dequeue()
    
    assert cmd1 == ".P0立即"
    assert cmd2 == ".P1高"
    assert cmd3 == ".P2正常"
    assert cmd4 == ".P3低优先级"


@pytest.mark.asyncio
async def test_command_queue_deduplication_with_callbacks():
    """Test that duplicated commands don't add multiple callbacks"""
    queue = CommandQueue()
    
    callback_count = {"count": 0}
    
    async def increment_callback():
        callback_count["count"] += 1
    
    # Enqueue same command twice with same dedupe key
    result1 = await queue.enqueue(
        ".duplicate",
        dedupe_key="dup:1",
        callback=increment_callback
    )
    result2 = await queue.enqueue(
        ".duplicate",
        dedupe_key="dup:1",
        callback=increment_callback
    )
    
    # First should succeed, second should be deduplicated
    assert result1 is True
    assert result2 is False
    
    # Only one command should be in queue
    cmd, key, callback = await queue.dequeue()
    assert cmd == ".duplicate"
    
    # Execute callback once
    if callback:
        await callback()
    
    # Callback should only execute once
    assert callback_count["count"] == 1
    
    # Queue should be empty
    assert queue.empty()


@pytest.mark.asyncio
async def test_command_queue_pending_count():
    """Test pending command count tracking"""
    queue = CommandQueue()
    
    # Initially empty
    assert queue.pending_count() == 0
    
    # Enqueue 3 commands
    await queue.enqueue("cmd1", dedupe_key="k1")
    await queue.enqueue("cmd2", dedupe_key="k2")
    await queue.enqueue("cmd3", dedupe_key="k3")
    
    assert queue.pending_count() == 3
    
    # Dequeue one
    cmd, key, _ = await queue.dequeue()
    assert queue.pending_count() == 3  # Still pending until marked complete
    
    # Mark as completed
    queue.mark_completed(key, success=True)
    assert queue.pending_count() == 2
    
    # Dequeue and complete the rest
    cmd2, key2, _ = await queue.dequeue()
    queue.mark_completed(key2, success=True)
    
    cmd3, key3, _ = await queue.dequeue()
    queue.mark_completed(key3, success=True)
    
    assert queue.pending_count() == 0


@pytest.mark.asyncio
async def test_bot_command_processor_with_callback():
    """Test bot's command processor handles callbacks correctly"""
    config = create_default_bot_config(-1001680975844, "测试频道")
    
    with patch('tg_signer.bot_worker.Client') as MockClient:
        bot = ChannelBot(
            config=config,
            account="test_account",
            workdir="/tmp/test_callback_bot"
        )
        
        # Mock the send_message to succeed
        mock_client_instance = MockClient.return_value
        mock_message = AsyncMock()
        mock_message.id = 12345
        mock_client_instance.send_message = AsyncMock(return_value=mock_message)
        bot.client = mock_client_instance
        
        # Set up callback tracking
        callback_executed = asyncio.Event()
        
        async def on_command_sent():
            callback_executed.set()
        
        # Enqueue command with callback
        dedupe_key = "test:callback:integration"
        await bot.command_queue.enqueue(
            ".test command",
            priority=1,
            dedupe_key=dedupe_key,
            callback=on_command_sent
        )
        
        # Manually process one command
        cmd, key, callback = await bot.command_queue.dequeue()
        success = await bot._send_command(cmd, key)
        
        # Mark as completed
        bot.command_queue.mark_completed(key, success)
        
        # Execute callback
        if callback:
            await callback()
        
        # Verify
        assert success is True
        assert callback_executed.is_set()
        assert bot.command_queue.get_state(dedupe_key) == "completed"


@pytest.mark.asyncio
async def test_activity_high_priority_execution():
    """Test that time-sensitive activities get P0 priority"""
    config = create_default_bot_config(-1001680975844, "测试频道")
    config.activity.enabled = True
    
    with patch('tg_signer.bot_worker.Client'):
        bot = ChannelBot(
            config=config,
            account="test_account",
            workdir="/tmp/test_activity_priority"
        )
        
        import time
        now = time.time()
        
        # Enqueue a normal command at current time
        await bot.command_queue.enqueue(
            ".normal command",
            when=now,
            priority=2,
            dedupe_key="normal:cmd"
        )
        
        # Enqueue a high-priority activity at the same time
        await bot.command_queue.enqueue(
            ".查看访客",
            when=now,
            priority=0,  # Activity priority
            dedupe_key="activity:urgent"
        )
        
        # The activity should come out first despite being enqueued second
        # because it has higher priority (lower number = higher priority)
        cmd1, _, _ = await bot.command_queue.dequeue()
        assert cmd1 == ".查看访客"
        
        cmd2, _, _ = await bot.command_queue.dequeue()
        assert cmd2 == ".normal command"
