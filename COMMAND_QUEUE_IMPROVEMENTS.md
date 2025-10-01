# 指令队列管理和模块协作优化说明

## 概述

本文档说明针对问题 #432b824b 的改进实现，主要解决以下三个核心需求：

1. **所有功能模块在初始化后首先解析加入队列，之后串行逐个执行**
2. **所有指令队列管理使用公用函数，支持状态管理和回调工厂**
3. **活动问答有时间限制的需要优先级处理**

## 改进内容

### 1. CommandQueue 类增强

#### 1.1 状态追踪系统

新增 `_command_states` 字典，追踪每个命令的完整生命周期：

```python
class CommandQueue:
    def __init__(self):
        self._queue = asyncio.PriorityQueue()
        self._pending = set()  # 去重键集合
        self._order = 0  # 保证相同优先级按FIFO顺序
        self._command_states = {}  # 状态追踪
        self._callbacks = {}  # 回调函数
```

**状态类型**：
- `pending`: 命令已入队，等待执行
- `executing`: 命令正在执行中
- `completed`: 命令执行成功
- `failed`: 命令执行失败

**使用示例**：
```python
# 入队时自动标记为 pending
await command_queue.enqueue(".宗门点卯", dedupe_key="daily:signin:123")
assert command_queue.get_state("daily:signin:123") == "pending"

# 出队时自动标记为 executing
cmd, key, callback = await command_queue.dequeue()
assert command_queue.get_state(key) == "executing"

# 执行完成后标记状态
command_queue.mark_completed(key, success=True)
assert command_queue.get_state(key) == "completed"
```

#### 1.2 回调机制

支持在命令执行完成后自动触发回调函数：

```python
async def after_signin():
    print("点卯完成，准备问安")
    await command_queue.enqueue(".每日问安", priority=1)

await command_queue.enqueue(
    ".宗门点卯",
    priority=0,
    dedupe_key="daily:signin",
    callback=after_signin  # 命令完成后自动调用
)
```

**回调特性**：
- 支持同步和异步回调函数
- 回调中可以继续入队后续命令，形成命令链
- 执行完成后自动清理回调，防止内存泄漏
- 仅在命令成功时执行回调

#### 1.3 增强的 API

```python
# 入队（支持回调）
async def enqueue(
    self, 
    command: str, 
    when: float = None,      # 执行时间戳
    priority: int = 2,       # 优先级 0-3
    dedupe_key: str = None,  # 去重键
    callback = None          # 回调函数
) -> bool:  # 返回是否成功入队

# 出队（返回3个值）
async def dequeue(self) -> tuple[str, Optional[str], Optional[callable]]:
    # 返回: (command, dedupe_key, callback)

# 标记完成
def mark_completed(self, dedupe_key: str, success: bool = True):

# 查询状态
def get_state(self, dedupe_key: str) -> Optional[str]:

# 获取待处理数量
def pending_count(self) -> int:
```

### 2. 统一消息发送层

#### 2.1 所有消息通过 _send_command 发送

**改进前**：
```python
# 各处直接发送消息
await message.reply(reply_text)  # ❌ 直接发送
await self.xiaozhi_client.send_message(text)  # ❌ 绕过队列
```

**改进后**：
```python
# 统一入队，由 _command_processor 串行处理
await self.command_queue.enqueue(
    reply_text,
    priority=2,
    dedupe_key=f"ai_reply:{user_id}:{time.time()}"
)  # ✅ 统一入队
```

#### 2.2 _command_processor 串行处理

```python
async def _command_processor(self):
    """后台任务，串行处理命令队列"""
    while self._running:
        if not self.command_queue.empty():
            # 1. 取出命令
            command, dedupe_key, callback = await self.command_queue.dequeue()
            
            # 2. 执行命令（包含速率控制）
            success = await self._send_command(command, dedupe_key)
            
            # 3. 标记完成状态
            if dedupe_key:
                self.command_queue.mark_completed(dedupe_key, success)
            
            # 4. 执行回调
            if callback and success:
                await callback()
        else:
            await asyncio.sleep(1)
```

**关键改进**：
- ✅ 串行执行：每个命令执行完才处理下一个
- ✅ 速率控制：统一的 `min_send_interval` 控制
- ✅ 状态追踪：自动更新命令状态
- ✅ 回调执行：成功后自动触发回调
- ✅ 错误处理：统一的异常捕获和日志

#### 2.3 _send_command 改进

```python
async def _send_command(self, command: str, dedupe_key: str = None) -> bool:
    """
    发送命令，返回成功/失败状态
    """
    # 速率限制
    now = time.time()
    elapsed = now - self._last_send_time
    if elapsed < self.config.min_send_interval:
        await asyncio.sleep(self.config.min_send_interval - elapsed)
    
    try:
        # 特殊处理（如传功需要 reply_to）
        reply_to_message_id = None
        if "宗门传功" in command:
            reply_to_message_id = self.daily_routine.state.last_message_id
        
        # 发送消息
        message = await self.client.send_message(
            self.config.chat_id,
            command,
            reply_to_message_id=reply_to_message_id
        )
        self._last_send_time = time.time()
        
        logger.info(f"✓ Sent command: {command}")
        return True  # 返回成功状态
        
    except Exception as e:
        logger.error(f"✗ Failed to send command '{command}': {e}")
        return False  # 返回失败状态
```

### 3. 优先级系统

#### 3.1 四级优先级定义

| 优先级 | 数值 | 用途 | 示例 |
|--------|------|------|------|
| P0 | 0 | 立即/最高优先级 | 活动响应（魂魄献祭、天机考验、洞府访客） |
| P1 | 1 | 高优先级 | 每日任务（点卯、问安、传功）、周期任务 |
| P2 | 2 | 正常优先级（默认） | 小药园、观星台、AI响应 |
| P3 | 3 | 低优先级 | 非紧急后台任务 |

#### 3.2 活动响应使用 P0 优先级

**需求背景**：活动问答有时间限制（通常15-30秒），必须立即响应。

**实现方式**：
```python
# activity_manager.py 中的活动定义
ActivityPattern(
    name="魂魄献祭",
    patterns=[r"回复本消息\s+\.献上魂魄"],
    response_type="reply_command",
    response_value=".收敛气息",
    priority=0  # ⭐ P0 最高优先级
)

ActivityPattern(
    name="天机考验",
    patterns=[r"【天机考验】", r"直接回复本消息"],
    response_type="ai_query",
    priority=0  # ⭐ P0 最高优先级
)
```

**入队处理**：
```python
# bot_worker.py 中的活动处理
if activity_match:
    response_command, response_type, priority = activity_match
    
    # 活动使用 priority=0 立即执行
    await self.command_queue.enqueue(
        response_command,
        priority=priority,  # 0 = 最高优先级
        dedupe_key=f"activity:{response_command}:{self.config.chat_id}"
    )
```

#### 3.3 优先级调度效果

```python
# 示例场景：同时有多个命令入队
await queue.enqueue(".小药园", priority=2)      # P2 - 正常
await queue.enqueue(".闭关修炼", priority=1)    # P1 - 高
await queue.enqueue(".查看访客", priority=0)    # P0 - 最高
await queue.enqueue(".每日问安", priority=1)    # P1 - 高

# 执行顺序：P0 -> P1 -> P1 -> P2
# 1. .查看访客  (P0 最高优先级，立即执行)
# 2. .闭关修炼  (P1 高优先级)
# 3. .每日问安  (P1 高优先级)
# 4. .小药园    (P2 正常优先级)
```

### 4. 模块初始化和协作流程

#### 4.1 Bot 启动流程

```python
async def start(self):
    """启动Bot"""
    self._running = True
    
    # 1. 启动 Telegram 客户端
    await self.client.start()
    
    # 2. 注册消息处理器
    self._register_handlers()
    
    # 3. 启动后台任务（命令处理器、每日重置）
    asyncio.create_task(self._command_processor())  # 串行处理命令
    asyncio.create_task(self._daily_reset_task())
    
    # 4. 启动所有功能模块（初始化并入队）
    await self.daily_routine.start()      # 入队每日任务
    await self.periodic_tasks.start()     # 入队周期任务
    await self.herb_garden.start()        # 入队药园扫描
    await self.star_observation.start()   # 入队观星任务
```

**关键点**：
- ✅ 所有模块的 `start()` 方法只负责解析和入队，不直接执行
- ✅ 入队后，命令进入优先级队列等待
- ✅ `_command_processor` 后台任务串行处理所有命令

#### 4.2 模块初始化示例

**每日任务模块**：
```python
async def start(self):
    """启动每日任务模块"""
    logger.info("[每日] 启动每日任务模块")
    
    # 解析需要执行的任务
    for command, priority, delay in self.get_next_commands():
        # 仅入队，不执行
        await self.command_queue.enqueue(
            command,
            when=time.time() + delay,
            priority=priority,
            dedupe_key=f"daily:{command}:{self.chat_id}"
        )
```

**周期任务模块**：
```python
async def start(self):
    """启动周期任务模块"""
    logger.info(f"[周期] 启动周期任务模块")
    
    # 调度就绪的任务
    for command, priority, delay in self.get_ready_tasks():
        # 仅入队，不执行
        await self.command_queue.enqueue(
            command,
            when=time.time() + delay,
            priority=priority,
            dedupe_key=f"periodic:{command}:{self.chat_id}"
        )
```

#### 4.3 消息处理流程

```python
async def _on_message(self, client: Client, message: Message):
    """处理接收到的消息"""
    handled = False
    
    # 按照 ARCHITECTURE.md 定义的顺序依次检查
    # Daily -> Periodic -> Star -> Herb -> Activity -> AI
    
    # 1. 每日任务
    if await self.daily_routine.handle_message(message):
        handled = True
    
    # 2. 周期任务
    if not handled and await self.periodic_tasks.handle_message(message):
        handled = True
    
    # 3. 观星台
    if not handled and await self.star_observation.handle_message(message):
        handled = True
    
    # 4. 小药园
    if not handled and await self.herb_garden.handle_message(message):
        handled = True
    
    # 5. 活动管理器（P0 优先级）
    if not handled and self.config.activity.enabled:
        activity_match = self.activity_manager.match_activity(message.text, message)
        if activity_match:
            response_command, response_type, priority = activity_match
            await self.command_queue.enqueue(
                response_command,
                priority=priority,  # 活动使用 P0
                dedupe_key=f"activity:{response_command}:{self.config.chat_id}"
            )
            handled = True
    
    # 6. AI 交互
    if not handled and self.xiaozhi_client:
        await self._handle_xiaozhi_message(message)
```

### 5. 测试验证

#### 5.1 命令队列增强测试 (8个测试)

1. **test_command_queue_state_tracking**: 状态追踪生命周期
2. **test_command_queue_callback_execution**: 回调执行
3. **test_command_queue_failed_state**: 失败状态标记
4. **test_command_queue_priority_levels**: 四级优先级排序
5. **test_command_queue_deduplication_with_callbacks**: 去重与回调交互
6. **test_command_queue_pending_count**: 待处理计数
7. **test_bot_command_processor_with_callback**: Bot命令处理器集成
8. **test_activity_high_priority_execution**: 活动高优先级

#### 5.2 模块集成测试 (7个测试)

1. **test_all_modules_initialization_and_enqueue**: 所有模块初始化和入队
2. **test_serial_command_execution**: 串行命令执行
3. **test_unified_command_queue_management**: 统一队列管理
4. **test_activity_time_sensitive_priority**: 活动时间敏感优先级
5. **test_message_handling_pipeline**: 消息处理流水线
6. **test_callback_chain_execution**: 回调链执行
7. **test_bot_full_lifecycle**: Bot完整生命周期

**测试结果**：✅ **147 个测试全部通过**

### 6. 使用示例

#### 6.1 基本命令入队

```python
# 简单命令
await command_queue.enqueue(
    ".宗门点卯",
    priority=0,
    dedupe_key="daily:signin:123"
)

# 延迟执行
await command_queue.enqueue(
    ".闭关修炼",
    when=time.time() + 60,  # 60秒后执行
    priority=1,
    dedupe_key="periodic:biguan:123"
)
```

#### 6.2 带回调的命令链

```python
async def after_first_transmission():
    """第一次传功完成后，安排第二次"""
    if bot.daily_routine.should_transmission():
        await bot.command_queue.enqueue(
            ".宗门传功",
            when=time.time() + 35,  # 35秒后
            priority=1,
            dedupe_key="daily:transmission2:123"
        )

# 第一次传功
await bot.command_queue.enqueue(
    ".宗门传功",
    priority=1,
    dedupe_key="daily:transmission1:123",
    callback=after_first_transmission
)
```

#### 6.3 活动优先响应

```python
# 识别到活动消息
if "【天机考验】" in message.text:
    # 使用 P0 优先级立即响应
    await bot.command_queue.enqueue(
        ai_answer,
        priority=0,  # 最高优先级
        dedupe_key=f"activity:tianji:{time.time()}"
    )
```

### 7. 架构优势

#### 7.1 符合 ARCHITECTURE.md 设计

- ✅ **模块化**: 各功能模块独立，通过统一队列协作
- ✅ **串行执行**: 所有命令通过 `_command_processor` 串行处理
- ✅ **状态管理**: 完整的命令状态追踪
- ✅ **优先级调度**: 支持4级优先级，确保紧急任务优先
- ✅ **速率控制**: 统一的发送间隔控制
- ✅ **可扩展**: 回调机制支持命令链和复杂逻辑

#### 7.2 解决的核心问题

1. **问题1**: ✅ 所有模块初始化后入队，串行执行
   - 每个模块的 `start()` 只负责解析和入队
   - `_command_processor` 确保串行处理
   - 状态追踪记录执行进度

2. **问题2**: ✅ 公用队列管理，状态管理，回调支持
   - 所有模块使用统一的 `command_queue.enqueue()`
   - 完整的状态追踪 (pending/executing/completed/failed)
   - 回调机制支持命令链

3. **问题3**: ✅ 活动时间敏感，优先级处理
   - 活动使用 P0 最高优先级
   - 优先级队列确保立即处理
   - 测试验证 P0 优先于其他优先级

### 8. 性能和可靠性

#### 8.1 性能优化

- **异步处理**: 所有操作都是异步的，不阻塞
- **高效队列**: 使用 `asyncio.PriorityQueue` 保证 O(log n) 复杂度
- **内存控制**: 执行完成后自动清理回调和状态

#### 8.2 可靠性保证

- **去重保护**: 防止重复命令
- **状态追踪**: 可以随时查询命令执行状态
- **错误处理**: 统一的异常捕获，不会因单个命令失败导致整体崩溃
- **速率控制**: 防止触发 Telegram 限流

### 9. 未来可选优化

超出当前需求范围的可选改进：

1. **命令重试机制**: 失败命令自动重试（指数退避）
2. **命令超时机制**: 执行超时自动标记失败
3. **Metrics 收集**: 统计命令执行成功率、延迟等
4. **Hook 扩展**: 更多的 hook 点（before_send, after_send, on_retry）
5. **持久化队列**: 队列状态持久化，重启后恢复

### 10. 总结

本次改进完全满足了原始需求：

1. ✅ **模块初始化后入队，串行执行**: 通过 `_command_processor` 实现
2. ✅ **统一队列管理，状态追踪，回调支持**: CommandQueue 全面增强
3. ✅ **活动时间敏感，优先级处理**: P0 优先级系统

同时保持了代码的：
- 简洁性：最小化改动，不破坏现有功能
- 可测试性：147个测试全部通过
- 可扩展性：支持回调链和未来扩展
- 可维护性：清晰的状态管理和错误处理

**测试验证**: ✅ **147/147 测试通过** (包括原有132个 + 新增15个)
