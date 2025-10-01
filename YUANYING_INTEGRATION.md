# 元婴任务集成说明 (YuanYing Tasks Integration)

## 概述

元婴任务（YuanYingTasks）已经完全集成到 bot_worker.py 的主工作流中，与其他模块（如 HerbGarden、StarObservatory 等）一样，**通过配置文件控制**，无需手动继承或额外集成。

## 配置控制

在 `example_bot_config.json` 或你的自定义配置文件中，通过以下字段控制元婴任务：

```json
{
  "periodic": {
    "enable_yuanying": true
  }
}
```

- `enable_yuanying: true` - 启用元婴任务自动化
- `enable_yuanying: false` - 禁用元婴任务

就这么简单！不需要任何额外的代码或继承。

## 工作原理

### 1. 自动初始化

在 `bot_worker.py` 的 `ChannelBot.__init__()` 中，YuanYingTasks 会自动初始化：

```python
# 自动初始化 YuanYing Tasks（元婴任务）
self.yuanying_tasks = YuanYingTasks(
    config, self.state_store, self.command_queue, config.chat_id, account
)
```

### 2. 自动启动

在 `ChannelBot.start()` 中，YuanYingTasks 会自动启动（如果配置启用）：

```python
# 启动 YuanYing tasks（如果启用）
await self.yuanying_tasks.start()
```

### 3. 自动消息处理

在 `ChannelBot._on_message()` 中，YuanYingTasks 会自动处理相关消息：

```python
# 首先检查 YuanYing tasks 模块
if await self.yuanying_tasks.handle_message(message):
    handled = True
    logger.debug("消息由 YuanYing tasks 处理")
```

## 功能说明

YuanYingTasks 会自动管理以下任务：

### 1. 元婴状态查询 (`.元婴状态`)

- 自动定期查询元婴状态
- 根据返回的冷却时间智能调度下次查询
- 识别三种状态：
  - **元神归窍** - 元婴满载而归，可以立即出窍
  - **元神出窍** - 元婴正在外游历，提取归来倒计时
  - **窍中温养** - 元婴在体内温养，检查是否可以出窍

### 2. 元婴出窍 (`.元婴出窍`)

- 当状态为"元神归窍"或"窍中温养可出窍"时，自动执行出窍
- 解析出窍结果（成功/失败）
- 提取冷却时间并安排下次查询
- 在元婴归来前 2 分钟安排预扫

### 3. 智能调度

- **基于 ETA 的调度**: 根据游戏返回的冷却时间动态调整
- **防止重复**: 使用去重键避免重复命令
- **优先级管理**: 元婴任务使用优先级 2（中优先级）
- **状态持久化**: 状态保存在 `yuanying_state.json` 文件中

## ActivityManager 集成

ActivityManager 也已经集成到消息处理循环中，用于识别和响应频道活动：

```python
# 检查 Activity Manager 进行活动匹配
if message.text and self.config.activity.enabled:
    activity_match = self.activity_manager.match_activity(
        message.text, 
        message,
        enable_ai=bool(self.xiaozhi_client and self.config.xiaozhi_ai.authorized_users)
    )
    if activity_match:
        response_command, response_type, priority = activity_match
        # 入队响应命令/文本
        await self.command_queue.enqueue(...)
```

## 与其他模块的一致性

所有模块现在都遵循相同的模式：

| 模块 | 配置字段 | 自动初始化 | 自动启动 | 消息处理 |
|------|---------|----------|---------|---------|
| YuanYingTasks | `periodic.enable_yuanying` | ✅ | ✅ | ✅ |
| ActivityManager | `activity.enabled` | ✅ | N/A | ✅ |
| HerbGarden | `herb_garden.enabled` | (未实现) | (未实现) | (未实现) |
| StarObservatory | `star_observation.enabled` | (未实现) | (未实现) | (未实现) |
| DailyRoutine | `daily.*` | (未实现) | (未实现) | (未实现) |
| PeriodicTasks | `periodic.*` | (未实现) | (未实现) | (未实现) |

**注意**: HerbGarden、StarObservatory 等模块在 PR #2 中实现，但未合并到当前分支。YuanYingTasks 和 ActivityManager 现在已经完整集成。

## 状态文件

YuanYingTasks 使用 `yuanying_state.json` 保存状态：

```json
{
  "acct_<account>_chat_<chat_id>": {
    "status": "归窍",
    "can_chuxiao": true,
    "last_check_ts": 1234567890.123,
    "next_check_ts": 1234567920.123,
    "last_chuxiao_ts": 1234567890.123,
    "return_countdown_seconds": 0,
    "chuxiao_cooldown": 28800
  }
}
```

## 日志输出

YuanYingTasks 会输出详细的日志信息：

```
[元婴] Starting YuanYing module
[元婴] Scheduled yuanying status check
[元婴] 识别状态: 元神归窍 - 可以立即出窍
[元婴] Scheduled yuanying chuxiao: .元婴出窍
[元婴] 出窍成功，冷却28800秒，将在归来前2分钟检查
```

## 示例配置

完整的配置示例参见 `example_bot_config.json`：

```json
{
  "chat_id": -1001234567890,
  "name": "仙门频道示例",
  "periodic": {
    "enable_qizhen": true,
    "enable_zhuzhen": true,
    "enable_wendao": true,
    "enable_yindao": true,
    "enable_yuanying": true,
    "enable_rift_explore": true
  },
  "activity": {
    "enabled": true,
    "rules_extra": []
  }
}
```

## 常见问题

### Q: 为什么不需要手动继承？

A: YuanYingTasks 已经作为 ChannelBot 的一个属性自动初始化和管理。所有配置通过 JSON 文件控制，遵循"配置驱动"的设计原则。

### Q: 如何临时禁用元婴任务？

A: 只需将配置文件中的 `periodic.enable_yuanying` 设为 `false` 并重启 bot。

### Q: 元婴任务和 PeriodicTasks 的关系？

A: YuanYingTasks 是专门处理元婴相关任务的模块，提供更智能的状态解析和调度。PeriodicTasks 模块（如果存在）可能提供基本的周期性 `.元婴状态` 调用，但功能较简单。两者可以共存，通过配置选择使用哪一个。

### Q: 如何查看元婴任务的状态？

A: 查看 `.bot/states/yuanying_state.json` 文件，或者查看日志输出。

## 总结

- ✅ YuanYingTasks 已完全集成到 bot_worker.py
- ✅ 通过配置文件 `periodic.enable_yuanying` 控制
- ✅ 无需手动继承或额外代码
- ✅ 与其他模块保持一致的设计模式
- ✅ ActivityManager 也已集成，用于活动识别和响应
- ✅ 所有功能都是配置驱动的
