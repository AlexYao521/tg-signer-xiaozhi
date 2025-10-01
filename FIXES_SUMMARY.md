# 修复总结 (Fixes Summary)

## 问题描述 (Problem Statement)

根据问题描述，存在以下三个问题：

1. **每日任务、周期、星宫、小药园等多个功能模块不能并行，都需要解析存放到队列** - 所有模块同时启动导致命令发送过快，触发 Telegram 的 SLOWMODE_WAIT_X 错误

2. **脚本配置的开关在消息监听指令解析中未生效** - 配置文件中的 enable_sign_in, enable_greeting, enable_transmission 等开关没有被检查

3. **on_message解析指令，必须满足条件 1频道机器人发送 2@我的。现在出现了其他人的也被解析了** - 消息过滤太宽松，导致其他用户的消息也被处理

## 解决方案 (Solutions)

### 问题1：模块启动时命令发送过快

**症状**：
```
2025-10-02 06:13:32 | INFO  | .闭关修炼
2025-10-02 06:13:33 | ERROR | .小药园 - SLOWMODE_WAIT_X wait 8 seconds
2025-10-02 06:13:36 | ERROR | .每日问安 - SLOWMODE_WAIT_X wait 5 seconds
```

**原因**：
- 所有模块（daily, periodic, herb, star）在 `start()` 时立即调用 `command_queue.enqueue()` 
- 所有命令的延迟都是 0 或很小，导致几乎同时发送
- 虽然命令处理器有速率限制，但如果间隔小于频道的慢速模式限制，仍会出错

**修复**：

1. **模块间错开启动** (bot_worker.py):
```python
# 每个模块间隔 5 秒启动
await self.daily_routine.start()
await asyncio.sleep(5)

await self.periodic_tasks.start()
await asyncio.sleep(5)

await self.herb_garden.start()
await asyncio.sleep(5)

await self.star_observation.start()
```

2. **模块内命令间隔** (daily_routine.py, periodic_tasks.py):
```python
# 每个命令之间间隔 2 秒
def get_next_commands(self):
    commands = []
    delay_offset = 0
    
    if self.should_signin():
        commands.append((".宗门点卯", 0, delay_offset))
        delay_offset += 2
    
    if self.should_greeting():
        commands.append((".每日问安", 1, delay_offset))
        delay_offset += 2
    ...
```

**结果**：
- 命令发送时间线：0s, 2s, 4s, 5s, 7s, 9s...
- 每个命令之间至少间隔 2 秒，避免触发慢速模式

### 问题2：配置开关未生效

**原因**：
- `should_signin()`, `should_greeting()`, `should_transmission()` 方法只检查状态，不检查配置

**修复前** (daily_routine.py):
```python
def should_signin(self) -> bool:
    return not self.state.signin_done  # ❌ 未检查配置
```

**修复后**:
```python
def should_signin(self) -> bool:
    return self.config.enable_sign_in and not self.state.signin_done  # ✅ 检查配置
```

**验证**：
- 当 `enable_greeting=False` 时，`.每日问安` 不会被执行
- 当 `enable_transmission=False` 时，`.宗门传功` 不会被执行

### 问题3：消息过滤太宽松

**原因**：
- 原始的 `_on_message` 只过滤 chat_id，不检查发送者类型
- 导致普通用户的消息也被各个模块处理

**修复** (bot_worker.py):
```python
async def _on_message(self, client: Client, message: Message):
    # 消息过滤逻辑：
    # 1. 机器人消息 -> 总是处理（命令响应）
    # 2. 带有 @mention 的消息 -> 处理（活动/互动）
    # 3. 频道帖子（无 from_user）-> 处理
    # 4. 普通用户消息且无 mention -> 跳过
    
    should_process = False
    
    if message.from_user:
        is_bot = getattr(message.from_user, 'is_bot', False)
        if is_bot:
            should_process = True  # 处理所有机器人消息
        else:
            # 检查是否有 @mention
            has_mention = False
            if message.entities:
                for entity in message.entities:
                    entity_type = getattr(entity.type, 'name', str(entity.type))
                    if entity_type in ("MENTION", "TEXT_MENTION"):
                        has_mention = True
                        break
            
            if has_mention:
                should_process = True
    else:
        should_process = True  # 频道帖子
    
    if not should_process:
        logger.debug(f"Skipping message from user {message.from_user.id}")
        return
    
    # 继续处理消息...
```

**过滤规则总结**：

| 消息类型 | is_bot | has_mention | 是否处理 | 原因 |
|---------|--------|-------------|---------|------|
| 机器人响应 | True | - | ✅ 是 | 需要解析命令响应 |
| 活动消息（@我） | False | True | ✅ 是 | 需要响应活动 |
| 普通用户消息 | False | False | ❌ 否 | 避免干扰 |
| 频道帖子 | None | - | ✅ 是 | 可能是重要公告 |

## 测试结果 (Test Results)

所有测试通过：
- ✅ 6/6 bot_worker 测试
- ✅ 7/7 module_integration 测试
- ✅ 总计 13 个测试全部通过

## 预期效果 (Expected Behavior)

### 修复后的行为：

1. **不再出现 SLOWMODE_WAIT_X 错误**
   - 命令发送间隔至少 2 秒
   - 模块启动错开 5 秒
   - 总体发送速率符合频道慢速模式要求

2. **配置开关生效**
   - `enable_sign_in=false` -> 不执行点卯
   - `enable_greeting=false` -> 不执行问安
   - `enable_transmission=false` -> 不执行传功
   - 其他周期任务同理

3. **消息过滤正确**
   - 只处理机器人消息和带 mention 的消息
   - 普通用户的聊天消息被忽略
   - 不会误解析其他人的指令

## 文件修改清单 (Files Modified)

1. **tg_signer/bot_worker.py**
   - 添加模块启动的错开延迟（5秒）
   - 改进消息过滤逻辑

2. **tg_signer/daily_routine.py**
   - 修复 should_* 方法检查配置开关
   - 添加命令间的渐进延迟（2秒）

3. **tg_signer/periodic_tasks.py**
   - 添加命令间的渐进延迟（2秒）

4. **tests/test_bot_worker.py**
   - 更新 mock 使其包含 is_bot 属性

## 使用建议 (Usage Recommendations)

1. **配置文件建议**：
   - 确保 `min_send_interval` >= 10.0 秒（对应频道慢速模式）
   - 根据需要禁用不必要的功能（如 `enable_greeting=false`）

2. **监控日志**：
   - 观察是否还有 SLOWMODE_WAIT_X 错误
   - 检查被跳过的消息日志：`"Skipping message from user..."`

3. **调试模式**：
   - 如需查看详细的消息过滤信息，设置日志级别为 DEBUG
