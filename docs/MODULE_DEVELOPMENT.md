# 模块开发指南

## 创建新模块

### 1. 创建模块文件

在 `tg_signer/modules/` 创建新文件，例如 `my_module.py`:

```python
import logging
from typing import Dict, Any

logger = logging.getLogger("tg-signer.my_module")


class MyModule:
    """
    My Custom Module
    
    Description of what this module does.
    """
    
    def __init__(
        self,
        config,
        state_store,
        command_queue,
        chat_id: int,
        account: str
    ):
        self.config = config  # Bot configuration
        self.state_store = state_store  # State persistence
        self.command_queue = command_queue  # Command queue
        self.chat_id = chat_id
        self.account = account
        
        # State key for this account/chat
        self.state_key = f"acct_{account}_chat_{chat_id}"
    
    async def start(self):
        """Initialize and start the module"""
        if not self.config.my_feature.enabled:
            logger.info("My module disabled")
            return
        
        logger.info("Starting my module")
        # Schedule initial tasks
        await self._schedule_initial_task()
    
    async def handle_message(self, message) -> bool:
        """
        Handle incoming message from the channel.
        
        Returns:
            True if message was handled, False otherwise
        """
        if not message.text:
            return False
        
        text = message.text
        
        # Parse and handle message
        if "keyword" in text:
            await self._handle_keyword(text)
            return True
        
        return False
    
    async def _schedule_initial_task(self):
        """Schedule initial task"""
        await self.command_queue.enqueue(
            ".my_command",
            priority=3,
            dedupe_key=f"my_module:task:{self.chat_id}"
        )
    
    async def _handle_keyword(self, text: str):
        """Handle keyword match"""
        logger.info(f"Handling keyword: {text}")
        
        # Update state
        state = self.state_store.load("my_module_state.json")
        module_state = state.get(self.state_key, {})
        
        module_state["last_action"] = time.time()
        
        state[self.state_key] = module_state
        self.state_store.save("my_module_state.json", state)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current module status"""
        state = self.state_store.load("my_module_state.json")
        module_state = state.get(self.state_key, {})
        
        return {
            "enabled": True,
            "last_action": module_state.get("last_action")
        }
```

### 2. 注册模块

在 `modules/__init__.py` 添加导出:

```python
from .my_module import MyModule

__all__ = [
    # ... existing modules
    "MyModule",
]
```

### 3. 集成到 ChannelBot

在 `bot_worker.py` 的 `__init__` 方法中初始化:

```python
from .modules import MyModule

class ChannelBot:
    def __init__(self, ...):
        # ... existing code
        
        # Initialize my module
        self.my_module = MyModule(
            config, self.state_store, self.command_queue,
            config.chat_id, account
        )
```

在 `start()` 方法中启动:

```python
async def start(self):
    # ... existing code
    await self.my_module.start()
```

在 `_on_message()` 中处理消息:

```python
async def _on_message(self, client, message):
    # ... existing code
    if await self.my_module.handle_message(message):
        handled = True
```

### 4. 添加配置支持

在 `bot_config.py` 添加配置类:

```python
class MyFeatureConfig(BaseModel):
    """My feature configuration"""
    enabled: bool = False
    option1: str = "default"
    option2: int = 100
```

在 `BotConfig` 中添加字段:

```python
class BotConfig(BaseModel):
    # ... existing fields
    my_feature: MyFeatureConfig = Field(default_factory=MyFeatureConfig)
```

## 最佳实践

### 状态管理

- 使用专用状态文件（如 `my_module_state.json`）
- 命名空间隔离：`acct_{account}_chat_{chat_id}`
- 使用 StateStore 的原子写入
- 记录时间戳（Unix timestamp）

### 命令调度

- 使用优先级：1=高优先级，5=低优先级
- 提供去重键（dedupe_key）避免重复
- 使用 `when` 参数进行定时调度
- 考虑速率限制

### 日志

- 使用模块专属 logger
- 记录关键操作和状态变化
- 使用适当的日志级别（debug/info/warning/error）

### 错误处理

- 捕获并记录异常
- 不要让单个错误崩溃整个机器人
- 提供降级策略

## 示例：简单计数器模块

```python
import logging
import time
from typing import Dict, Any

logger = logging.getLogger("tg-signer.counter")


class CounterModule:
    """Simple counter module example"""
    
    def __init__(self, config, state_store, command_queue, chat_id, account):
        self.config = config
        self.state_store = state_store
        self.command_queue = command_queue
        self.chat_id = chat_id
        self.account = account
        self.state_key = f"acct_{account}_chat_{chat_id}"
    
    async def start(self):
        """Start the module"""
        logger.info("Counter module started")
    
    async def handle_message(self, message) -> bool:
        """Handle messages with counting"""
        if not message.text or "count" not in message.text.lower():
            return False
        
        # Load state
        state = self.state_store.load("counter_state.json")
        counter_state = state.get(self.state_key, {"count": 0})
        
        # Increment counter
        counter_state["count"] += 1
        counter_state["last_count_time"] = time.time()
        
        # Save state
        state[self.state_key] = counter_state
        self.state_store.save("counter_state.json", state)
        
        logger.info(f"Counter: {counter_state['count']}")
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get status"""
        state = self.state_store.load("counter_state.json")
        counter_state = state.get(self.state_key, {})
        return {
            "count": counter_state.get("count", 0),
            "last_count_time": counter_state.get("last_count_time")
        }
```

## 测试

创建测试文件 `tests/test_my_module.py`:

```python
import pytest
from tg_signer.modules.my_module import MyModule


def test_my_module_initialization():
    # Test module initialization
    pass


def test_my_module_message_handling():
    # Test message handling
    pass
```

运行测试:

```bash
pytest tests/test_my_module.py
```

## 调试

启用调试日志:

```bash
tg-signer --log-level debug bot -a account run script
```

查看模块日志:

```bash
tail -f tg-signer.log | grep "my_module"
```
