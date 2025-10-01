# 集成状态报告 (Integration Status Report)

## 已完成集成 ✅

### 1. YuanYingTasks (元婴任务)
- **文件**: `tg_signer/yuanying_tasks.py`
- **状态**: ✅ 完全集成到 bot_worker.py
- **配置**: `periodic.enable_yuanying`
- **功能**:
  - 自动查询元婴状态 (`.元婴状态`)
  - 自动元婴出窍 (`.元婴出窍`)
  - 智能调度和状态管理
  - 基于 ETA 的任务调度

### 2. ActivityManager (活动管理器)
- **文件**: `tg_signer/activity_manager.py`
- **状态**: ✅ 完全集成到 bot_worker.py
- **配置**: `activity.enabled`
- **功能**:
  - 活动识别和响应
  - 魂魄献祭、天机考验、虚天殿问答、洞府访客等
  - 支持 AI 查询
  - 可扩展的活动规则

## 待集成模块 ⏳

以下模块在代码库中存在，但**尚未集成到 bot_worker.py**：

### 3. DailyRoutine (每日例行任务)
- **文件**: `tg_signer/daily_routine.py`
- **状态**: ⏳ 代码存在但未集成
- **配置**: `daily.enable_sign_in`, `daily.enable_transmission`, `daily.enable_greeting`
- **功能**:
  - 宗门点卯
  - 宗门传功（每日最多3次）
  - 每日问安
- **需要**: 转换为模块模式并集成到 bot_worker.py

### 4. PeriodicTasks (周期任务)
- **文件**: `tg_signer/periodic_tasks.py`
- **状态**: ⏳ 代码存在但未集成
- **配置**: `periodic.enable_qizhen`, `periodic.enable_zhuzhen`, 等
- **功能**:
  - 闭关修炼（16分钟）
  - 引道（12小时）
  - 启阵（12小时）
  - 问道（12小时）
  - 探寻裂缝（12小时）
- **需要**: 转换为模块模式并集成到 bot_worker.py
- **注意**: 与 YuanYingTasks 类似，但功能更通用

### 5. HerbGarden (小药园)
- **文件**: `tg_signer/herb_garden.py`
- **状态**: ⏳ 代码存在但未集成
- **配置**: `herb_garden.enabled`
- **功能**:
  - 自动扫描药园状态
  - 自动维护（除草、除虫、浇水）
  - 自动采药
  - 自动播种
  - 种子兑换
- **需要**: 转换为模块模式并集成到 bot_worker.py

### 6. StarObservation (观星台)
- **文件**: `tg_signer/star_observation.py`
- **状态**: ⏳ 代码存在但未集成
- **配置**: `star_observation.enabled`
- **功能**:
  - 自动观察星辰
  - 星辰牵引（序列轮转）
  - 收集精华
  - 星辰安抚
- **需要**: 转换为模块模式并集成到 bot_worker.py

## PR #2 中提到的模块

根据 PR #2 的描述，以下模块应该已经实现：

| 模块 | PR #2 状态 | 当前状态 | 说明 |
|------|-----------|---------|------|
| YuanYingTasks | ✅ | ✅ | 已集成 |
| ActivityManager | ✅ | ✅ | 已集成 |
| HerbGarden | ✅ | ⏳ | 代码存在但未集成 |
| StarObservatory | ✅ | ⏳ | 代码存在但未集成 |
| DailyRoutine | ✅ | ⏳ | 代码存在但未集成 |
| PeriodicTasks | ✅ | ⏳ | 代码存在但未集成 |

## 集成模式

所有模块应该遵循统一的集成模式：

### 1. 模块结构

```python
class ModuleName:
    def __init__(self, config, state_store, command_queue, chat_id, account):
        self.config = config.module_section
        self.state_store = state_store
        self.command_queue = command_queue
        self.chat_id = chat_id
        self.account = account
        self.state_key = f"acct_{account}_chat_{chat_id}"
    
    async def start(self):
        """启动模块"""
        if not self.config.enabled:
            logger.info("Module disabled")
            return
        logger.info("Starting module")
        # 初始化和调度
    
    async def handle_message(self, message) -> bool:
        """处理消息"""
        if not message.text:
            return False
        # 解析和处理
        return handled
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {...}
```

### 2. Bot Worker 集成

在 `bot_worker.py` 中：

```python
# 1. 导入
from .module_name import ModuleName

# 2. __init__ 中初始化
self.module = ModuleName(
    config, self.state_store, self.command_queue, 
    config.chat_id, account
)

# 3. start() 中启动
await self.module.start()

# 4. _on_message() 中处理
if await self.module.handle_message(message):
    handled = True
```

### 3. 配置驱动

所有功能通过配置文件控制：

```json
{
  "module_section": {
    "enabled": true,
    "option1": "value1"
  }
}
```

## 下一步行动

要完成所有模块的集成，需要：

1. **DailyRoutine**: 
   - 重构为模块模式（添加 async start 和 handle_message）
   - 集成到 bot_worker.py
   - 测试点卯、传功、问安功能

2. **PeriodicTasks**:
   - 重构为模块模式
   - 集成到 bot_worker.py
   - 与 YuanYingTasks 协调（避免重复）

3. **HerbGarden**:
   - 重构为模块模式
   - 集成到 bot_worker.py
   - 测试完整的药园自动化流程

4. **StarObservation**:
   - 重构为模块模式
   - 集成到 bot_worker.py
   - 测试观星台自动化流程

## 当前优先级

✅ **P0 (已完成)**: YuanYingTasks + ActivityManager 集成

📝 **P1 (建议下一步)**: 
- DailyRoutine (因为点卯、传功是基础日常任务)
- PeriodicTasks (因为配置已经存在)

📝 **P2 (可选增强)**:
- HerbGarden (小药园自动化)
- StarObservation (观星台自动化)

## 总结

✅ **当前已完成**: YuanYingTasks 和 ActivityManager 已完全集成，遵循配置驱动原则

⏳ **待完成**: DailyRoutine、PeriodicTasks、HerbGarden、StarObservation 需要按照相同模式进行集成

这是一个**渐进式集成**的方案，优先完成核心功能（元婴任务和活动管理），其他模块可以逐步集成。
