# 修仙机器人项目架构文档 (Project Architecture)

## 目录

1. [项目概述](#1-项目概述)
2. [整体架构](#2-整体架构)
3. [模块详细说明](#3-模块详细说明)
4. [数据流图](#4-数据流图)
5. [状态管理](#5-状态管理)
6. [冷却系统](#6-冷却系统)
7. [日志系统](#7-日志系统)
8. [配置管理](#8-配置管理)
9. [错误处理](#9-错误处理)
10. [测试策略](#10-测试策略)

---

## 1. 项目概述

### 1.1 项目目标

修仙机器人是一个自动化Telegram频道互动系统，主要功能包括：
- 每日例行任务自动化（点卯、传功、问安）
- 周期性任务管理（闭关、引道、问道、探寻裂缝等）
- 星宫观星台自动化（安抚、牵引、收集）
- 小药园自动化（维护、采药、播种）
- 活动识别与智能响应
- 小智AI对话集成

### 1.2 技术栈

- **语言**: Python 3.9+
- **Telegram客户端**: Pyrogram (kurigram 2.2.7)
- **配置管理**: Pydantic
- **日志**: Python logging + RotatingFileHandler
- **状态存储**: JSON文件（原子写入）
- **任务调度**: asyncio + PriorityQueue

### 1.3 核心特性

- ✅ 模块化设计，独立Python文件
- ✅ 冷却时间智能解析与管理
- ✅ 多账号支持，独立状态和日志
- ✅ 优先级队列与去重机制
- ✅ 星宫操作正确顺序（安抚→观星台）
- ✅ 活动自动识别与响应
- ✅ 小智AI集成支持

---

## 2. 整体架构

### 2.1 架构图

```
┌─────────────────────────────────────────────────────────┐
│                      CLI / Console                        │
│              (账号选择、配置管理、启动/停止)                │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                  ChannelBot (核心控制器)                  │
│  - 初始化客户端                                            │
│  - 注册消息处理器                                          │
│  - 启动后台任务                                            │
│  - 管理命令队列                                            │
└─────┬───────┬───────┬───────┬───────┬───────┬───────────┘
      │       │       │       │       │       │
      ▼       ▼       ▼       ▼       ▼       ▼
┌─────────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌─────────┐
│  Daily  │ │Star  │ │Herb  │ │Perio-│ │Activ-│ │Xiaozhi  │
│ Routine │ │Obser-│ │Garden│ │dic   │ │ity   │ │AI       │
│         │ │vation│ │      │ │Tasks │ │Mgr   │ │Client   │
└────┬────┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └────┬────┘
     │         │        │        │        │          │
     └─────────┴────────┴────────┴────────┴──────────┘
                      │
                      ▼
            ┌──────────────────┐
            │  Command Queue   │
            │  (优先级+去重)     │
            └────────┬─────────┘
                     │
                     ▼
            ┌──────────────────┐
            │ Telegram Client  │
            │   (Pyrogram)     │
            └────────┬─────────┘
                     │
                     ▼
            ┌──────────────────┐
            │  Telegram API    │
            └──────────────────┘
```

### 2.2 分层说明

| 层级 | 组件 | 职责 |
|-----|------|------|
| 表现层 | CLI | 命令行交互、账号管理 |
| 控制层 | ChannelBot | 生命周期管理、消息路由 |
| 业务层 | 各功能模块 | 业务逻辑实现 |
| 调度层 | CommandQueue | 任务排队、去重、优先级 |
| 通信层 | Telegram Client | API调用、消息收发 |
| 存储层 | StateStore | 状态持久化 |

---

## 3. 模块详细说明

### 3.1 核心模块

#### 3.1.1 bot_worker.py
**职责**: 机器人核心控制器

**主要类**:
- `ChannelBot`: 频道机器人主类
- `CommandQueue`: 优先级命令队列
- `StateStore`: 状态存储管理器

**核心方法**:
- `start()`: 启动机器人
- `stop()`: 停止机器人
- `_on_message()`: 消息处理入口
- `_command_processor()`: 命令队列处理器
- `_daily_reset_task()`: 每日重置任务

**依赖**: 所有功能模块

#### 3.1.2 daily_routine.py
**职责**: 每日例行任务管理

**核心类**:
- `DailyRoutine`: 每日任务管理器
- `DailyState`: 每日状态数据类

**支持任务**:
- 宗门点卯 (`.宗门点卯`)
- 每日问安 (`.每日问安`)
- 宗门传功 (`.宗门传功`, 最多3次)

**关键方法**:
- `should_signin()`: 检查是否需要点卯
- `should_greeting()`: 检查是否需要问安
- `should_transmission()`: 检查是否需要传功
- `parse_response()`: 解析响应并更新状态
- `reset_daily()`: 每日重置

**状态字段**:
```python
{
    "signin_done": bool,
    "greeting_done": bool,
    "transmission_count": int,  # 0-3
    "last_message_id": int,  # 用于传功回复
}
```

#### 3.1.3 star_observation.py
**职责**: 星宫观星台自动化

**核心类**:
- `StarObservation`: 星宫管理器
- `StarPlate`: 引星盘数据类
- `StarState`: 星辰状态枚举

**星辰状态**:
- `READY`: 精华已成（可收集）
- `IDLE`: 空闲（可牵引）
- `CONDENSING`: 凝聚中（等待）
- `AGITATED`: 星光黯淡（需安抚）

**核心逻辑**:
```
启动流程（关键设计）：
1. .安抚星辰 (P0优先级)
2. 等待3-6秒
3. .观星台 (P1优先级)
4. 解析状态并生成后续指令
```

**关键方法**:
- `get_startup_commands()`: 获取启动指令（安抚→观星台）
- `parse_pacify_response()`: 解析安抚响应
- `parse_observation_response()`: 解析观星台状态
- `parse_collect_response()`: 解析收集响应
- `parse_pull_response()`: 解析牵引响应

**状态字段**:
```python
{
    "last_pacify_ts": float,  # 上次安抚时间
    "sequence_index": int,     # 序列索引
    "plates": [                # 引星盘列表
        {
            "idx": int,
            "star_name": str,
            "state": str,
            "remain_seconds": int
        }
    ]
}
```

#### 3.1.4 periodic_tasks.py
**职责**: 周期性任务管理

**核心类**:
- `PeriodicTasks`: 周期任务管理器
- `TaskCooldown`: 任务冷却状态

**支持任务**:
- 闭关修炼 (16分钟)
- 引道 (12小时)
- 启阵 (12小时)
- 问道 (12小时)
- 探寻裂缝 (12小时)

**关键方法**:
- `should_execute()`: 检查任务是否可执行
- `get_ready_tasks()`: 获取就绪任务列表
- `parse_response()`: 解析响应并更新冷却
- `mark_task_executed()`: 手动标记任务执行

**特殊逻辑**:
- 探寻裂缝失败（风暴/受创）会安排预热
- 冷却时间从响应文本智能解析
- 解析失败自动使用默认值

#### 3.1.5 herb_garden.py
**职责**: 小药园自动化

**核心类**:
- `HerbGarden`: 药园管理器
- `Plot`: 地块数据类
- `PlotState`: 地块状态枚举

**地块状态**:
- `MATURE`: 已成熟（可采药）
- `PEST`: 害虫侵扰（需除虫）
- `WEED`: 杂草横生（需除草）
- `DRY`: 灵气干涸（需浇水）
- `GROWING`: 生长中（等待）
- `IDLE`: 空闲（可播种）

**操作流程**:
```
1. 扫描 (.小药园)
2. 维护 (P0): .除虫 / .除草 / .浇水
3. 采药 (P1): .采药
4. 播种 (P1): .播种 <地块> <种子>
```

**关键方法**:
- `should_scan()`: 检查是否需要扫描
- `parse_scan_response()`: 解析扫描结果
- `parse_maintenance_response()`: 解析维护响应
- `parse_harvest_response()`: 解析采药响应
- `generate_planting_commands()`: 生成播种指令

#### 3.1.6 activity_manager.py
**职责**: 活动识别与响应

**核心类**:
- `ActivityManager`: 活动管理器
- `ActivityPattern`: 活动模式定义

**支持活动** (基于活动回复词.md):
1. 魂魄献祭 → `.收敛气息`
2. 天机考验（选择题）→ AI查询答案
3. 天机考验（指令题）→ `.我的宗门`
4. 虚天殿问答 → `.作答 <选项>`
5. 洞府访客 → `.查看访客` / `.接待访客`

**关键方法**:
- `match_activity()`: 匹配活动模式
- `should_respond_to_message()`: 检查是否应响应
- `filter_message_by_thread()`: 按话题过滤消息
- `_query_xiaozhi()`: 查询小智AI获取答案

**消息过滤逻辑**:
```python
条件：
1. 必须是频道机器人消息
2. 必须@了机器人
3. 如果是回复，回复ID必须匹配
4. 不在排除的message_thread_id中
```

### 3.2 工具模块

#### 3.2.1 cooldown_parser.py
**职责**: 冷却时间解析

**核心函数**:
- `_extract_cooldown_seconds()`: 提取冷却秒数
- `extract_cooldown_with_fallback()`: 提取冷却（带默认值）
- `parse_time_remaining()`: 解析剩余时间
- `format_cooldown()`: 格式化冷却时间

**支持格式**:
- "12小时30分钟" → 45000秒
- "3分钟20秒" → 200秒
- "45秒" → 45秒

**容错机制**:
- 全角/半角字符自动转换
- 多余空格自动去除
- 解析失败使用默认值
- 异常值检测（小于10分钟）

#### 3.2.2 cooldown_config.py
**职责**: 冷却时间配置

**配置字典**:
- `DAILY_COOLDOWNS`: 每日任务冷却
- `PERIODIC_COOLDOWNS`: 周期任务冷却
- `STAR_PULL_COOLDOWNS`: 星辰牵引冷却
- `HERB_GARDEN_COOLDOWNS`: 药园冷却
- `SEED_MATURITY_HOURS`: 种子成熟时间

**核心函数**:
- `get_default_cooldown()`: 获取默认冷却
- `get_star_pull_cooldown()`: 获取星辰冷却
- `get_seed_maturity_hours()`: 获取种子成熟时间

#### 3.2.3 logger.py
**职责**: 日志管理

**核心函数**:
- `configure_logger()`: 配置全局logger
- `get_account_logger()`: 获取账号专属logger

**特性**:
- 支持按账号分离日志文件
- 日志目录结构: `logs/<account>/<account>.log`
- RotatingFileHandler自动轮转
- 控制台输出+文件输出

---

## 4. 数据流图

### 4.1 消息处理流程

```
Telegram频道消息
    │
    ▼
ChannelBot._on_message()
    │
    ├─→ Xiaozhi AI检测
    │   └─→ 触发关键词 → 发送给小智 → 回复
    │
    ├─→ 自定义规则检测
    │   └─→ 模式匹配 → 执行响应
    │
    └─→ 活动识别
        │
        ├─→ ActivityManager.match_activity()
        │   ├─→ 匹配活动模式
        │   ├─→ 检查@mention
        │   └─→ 生成响应指令
        │
        ├─→ DailyRoutine.parse_response()
        │   └─→ 更新每日任务状态
        │
        ├─→ StarObservation.parse_*_response()
        │   └─→ 更新星宫状态
        │
        ├─→ HerbGarden.parse_*_response()
        │   └─→ 更新药园状态
        │
        └─→ PeriodicTasks.parse_response()
            └─→ 更新周期任务冷却
```

### 4.2 指令发送流程

```
模块生成指令
    │
    ▼
CommandQueue.enqueue()
    │
    ├─→ 检查去重键
    ├─→ 设置优先级
    ├─→ 设置执行时间
    └─→ 加入优先级队列
        │
        ▼
CommandQueue.dequeue()
    │
    ├─→ 等待执行时间
    ├─→ 移除去重键
    └─→ 返回指令
        │
        ▼
ChannelBot._send_command()
    │
    ├─→ 检查速率限制
    ├─→ 发送消息
    ├─→ 记录发送时间
    └─→ 等待响应
        │
        ▼
Telegram API
```

### 4.3 启动流程

```
main() / CLI
    │
    ▼
创建ChannelBot实例
    │
    ├─→ 加载配置 (BotConfig)
    ├─→ 初始化StateStore
    ├─→ 创建CommandQueue
    ├─→ 创建Telegram Client
    └─→ 创建Xiaozhi Client (可选)
        │
        ▼
ChannelBot.start()
    │
    ├─→ 启动Telegram Client
    ├─→ 启动Xiaozhi Client
    ├─→ 注册消息处理器
    ├─→ 启动后台任务
    │   ├─→ _command_processor()
    │   └─→ _daily_reset_task()
    │
    ├─→ 加载各模块状态
    │   ├─→ DailyRoutine.load_state()
    │   ├─→ StarObservation.load_state()
    │   ├─→ HerbGarden.load_state()
    │   └─→ PeriodicTasks.load_state()
    │
    └─→ 安排初始任务
        ├─→ 每日任务 (如果未完成)
        ├─→ 星宫启动 (安抚→观星台)
        └─→ 周期任务 (如果冷却结束)
```

---

## 5. 状态管理

### 5.1 状态文件结构

```
.bot/states/
├── daily_state.json
├── star_state.json
├── herb_state.json
└── periodic_state.json
```

### 5.2 状态存储机制

**原子写入**:
1. 写入临时文件 (`.tmp`)
2. 成功后重命名覆盖原文件
3. 失败时删除临时文件

**命名空间**:
```
acct_<account>_chat_<chat_id>
```

### 5.3 状态同步

- 每次操作后立即保存
- 异常情况自动备份
- 启动时自动恢复

---

## 6. 冷却系统

### 6.1 冷却时间定义

参见 [COOLDOWN_RULES.md](./COOLDOWN_RULES.md)

### 6.2 冷却解析流程

```python
响应文本
    │
    ▼
_extract_cooldown_seconds(text, command)
    │
    ├─→ 标准化文本
    ├─→ 正则匹配
    ├─→ 提取小时/分钟/秒
    ├─→ 计算总秒数
    ├─→ 异常值检测
    └─→ 返回秒数 or None
        │
        ▼
extract_cooldown_with_fallback(text, command)
    │
    ├─→ 调用_extract_cooldown_seconds
    └─→ 失败时返回get_default_cooldown(command)
```

### 6.3 冷却管理

**去重键格式**:
```
<domain>:<action>:<chat>:<optional_suffix>
```

**示例**:
- `daily:signin:-1001234567890`
- `star:collect:-1001234567890`
- `star:pull:-1001234567890:1`
- `periodic:biguan:-1001234567890`

---

## 7. 日志系统

### 7.1 日志级别

- `DEBUG`: 详细调试信息
- `INFO`: 常规操作记录
- `WARNING`: 警告信息（解析失败等）
- `ERROR`: 错误信息
- `CRITICAL`: 严重错误

### 7.2 日志格式

```
[级别] [模块] 时间 文件 行号 消息
```

**示例**:
```
[INFO] [tg-signer.daily] 2024-01-01 08:00:00 daily_routine.py 123 [每日] 点卯成功
[WARNING] [tg-signer.cooldown] 2024-01-01 08:00:01 cooldown_parser.py 45 [冷却解析] 解析失败，使用默认冷却
```

### 7.3 日志TAG规范

- `[每日]`: 每日任务
- `[星宫]`: 星宫操作
- `[药园]`: 小药园
- `[周期]`: 周期任务
- `[活动]`: 活动响应
- `[队列]`: 命令队列
- `[错误]`: 错误信息
- `[冷却解析]`: 冷却时间解析

### 7.4 账号日志分离

```
logs/
├── account1/
│   └── account1.log
├── account2/
│   └── account2.log
└── tg-signer.log  (通用日志)
```

---

## 8. 配置管理

### 8.1 配置文件

**bot_config.json** (示例):
```json
{
  "chat_id": -1001234567890,
  "name": "仙门频道",
  "daily": {
    "enable_sign_in": true,
    "enable_transmission": true,
    "enable_greeting": false
  },
  "periodic": {
    "enable_qizhen": true,
    "enable_wendao": true,
    "enable_yindao": true,
    "enable_rift_explore": true
  },
  "star_observation": {
    "enabled": true,
    "default_star": "天雷星",
    "plate_count": 5,
    "sequence": ["天雷星", "赤血星", "庚金星"]
  },
  "herb_garden": {
    "enabled": true,
    "default_seed": "凝血草种子",
    "scan_interval_min": 900
  },
  "xiaozhi_ai": {
    "authorized_users": [12345678],
    "trigger_keywords": ["@小智", "小智AI"]
  },
  "sign_interval": 10.0,
  "min_send_interval": 1.0
}
```

### 8.2 配置类

**BotConfig** (Pydantic模型):
- 类型验证
- 默认值
- 嵌套配置
- JSON序列化

---

## 9. 错误处理

### 9.1 错误分类

| 类型 | 处理策略 |
|-----|---------|
| 网络错误 | 指数退避重试 |
| 解析错误 | 使用默认值 + WARNING |
| 配置错误 | 启动失败 + ERROR |
| 状态错误 | 自动恢复 + INFO |

### 9.2 重试机制

```python
最大重试次数: 3
退避策略: 指数 (2^n 秒)
抖动: ±20%
```

### 9.3 熔断机制

- 连续失败N次后暂停任务
- 等待恢复时间后重新启用
- 记录熔断事件

---

## 10. 测试策略

### 10.1 单元测试

**覆盖模块**:
- `cooldown_parser.py`: 冷却解析
- `cooldown_config.py`: 配置获取
- 各模块的状态解析函数

**工具**: pytest

### 10.2 集成测试

**覆盖场景**:
- 命令队列优先级
- 去重机制
- 状态持久化
- 模块协作

### 10.3 测试数据

创建 `tests/fixtures/` 目录存放测试数据：
- 响应文本样本
- 配置文件样本
- 状态文件样本

---

## 附录

### A. 文件清单

**核心模块**:
- `tg_signer/bot_worker.py` - 机器人核心
- `tg_signer/daily_routine.py` - 每日任务
- `tg_signer/star_observation.py` - 星宫管理
- `tg_signer/periodic_tasks.py` - 周期任务
- `tg_signer/herb_garden.py` - 小药园
- `tg_signer/activity_manager.py` - 活动管理

**工具模块**:
- `tg_signer/cooldown_parser.py` - 冷却解析
- `tg_signer/cooldown_config.py` - 冷却配置
- `tg_signer/logger.py` - 日志管理

**配置模块**:
- `tg_signer/bot_config.py` - Bot配置
- `tg_signer/config.py` - 通用配置

**文档**:
- `ARCHITECTURE.md` - 原始架构设计
- `PROJECT_ARCHITECTURE.md` - 项目架构文档（本文件）
- `COOLDOWN_RULES.md` - 冷却规则文档
- `活动回复词.md` - 活动响应规范

### B. 依赖关系

```
bot_worker.py
    ├── daily_routine.py
    ├── star_observation.py
    ├── periodic_tasks.py
    ├── herb_garden.py
    ├── activity_manager.py
    ├── cooldown_parser.py
    ├── cooldown_config.py
    ├── logger.py
    └── bot_config.py

cooldown_parser.py
    └── cooldown_config.py

各功能模块
    └── cooldown_parser.py
```

### C. 优先级定义

| 优先级 | 值 | 用途 |
|-------|---|------|
| P0 | 0 | 高价值操作（收集精华、采药、安抚） |
| P1 | 1 | 常规操作（点卯、问安、牵引） |
| P2 | 2 | AI回复、查询 |
| P3 | 3 | 低优先级任务 |

### D. 去重键规范

格式: `<domain>:<action>:<chat>[:<suffix>]`

**域名**:
- `daily`: 每日任务
- `star`: 星宫
- `herb`: 药园
- `periodic`: 周期任务
- `yuanying`: 元婴
- `activity`: 活动
- `ai`: AI回复

---

**文档版本**: 1.0  
**最后更新**: 2024-01  
**维护者**: 开发团队
