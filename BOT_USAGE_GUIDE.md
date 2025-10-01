# 频道自动化机器人使用指南

## 快速开始

### 1. 初始化配置

首次使用时，运行初始化命令来自动设置所有必要的配置：

```bash
tg-signer bot init
```

这个命令会：
- 创建所需的目录结构（`config/`, `bot_configs/`, `bot_workdir/`）
- 将 `config.json` 和 `efuse.json` 移至 `config/` 文件夹
- 提示配置 Telegram API 凭据（TG_API_ID 和 TG_API_HASH）
- 提示配置代理（例如：`socks5://127.0.0.1:7897`）
- 创建示例配置文件

### 2. 登录 Telegram 账号

```bash
tg-signer -a 账号名 login
```

按照提示输入手机号和验证码完成登录。

### 3. 创建机器人配置

**方式一：交互式配置（推荐）**

```bash
tg-signer bot config 我的机器人
```

按照提示回答问题，系统会自动生成配置文件。

**方式二：手动创建配置文件**

在 `.signer/bot_configs/` 目录下创建 JSON 配置文件，参考 [配置示例](#配置示例)。

### 4. 运行机器人

```bash
# 运行机器人（不启用AI聊天互动，但保留活动问答）
tg-signer -a 账号名 bot run 我的机器人

# 运行机器人并启用小智AI聊天互动
tg-signer -a 账号名 bot run 我的机器人 --ai

# 使用代理运行
tg-signer -a 账号名 -p socks5://127.0.0.1:7897 bot run 我的机器人 --ai
```

## CLI 命令详解

### `tg-signer bot init`

智能初始化 tg-signer 配置。

**功能：**
- 创建目录结构
- 迁移配置文件
- 配置 API 凭据和代理
- 生成示例配置

### `tg-signer bot config <配置名>`

交互式创建或修改机器人配置。

**示例：**
```bash
tg-signer bot config my_channel
```

### `tg-signer bot run <配置名> [--ai]`

运行指定的机器人配置。

**参数：**
- `<配置名>`: 配置文件名称（不含 .json 后缀）
- `--ai`: 启用小智AI聊天互动
- `-x, --xiaozhi-config`: 指定小智AI配置文件路径（默认：`config/config.json`）

**注意：**
- 不使用 `--ai` 标志时，小智客户端仍会初始化用于活动问答（如天机考验等）
- 使用 `--ai` 标志时，额外启用聊天消息的AI互动功能

**示例：**
```bash
# 基本运行
tg-signer -a my_account bot run my_channel

# 启用AI聊天互动
tg-signer -a my_account bot run my_channel --ai

# 指定小智配置文件
tg-signer -a my_account bot run my_channel --ai -x /path/to/config.json
```

### `tg-signer bot list`

列出所有已配置的机器人。

### `tg-signer bot doctor [配置名]`

检查配置和环境。

**示例：**
```bash
# 检查整体环境
tg-signer bot doctor

# 检查特定配置
tg-signer bot doctor my_channel
```

### `tg-signer bot export <配置名> [-o 输出文件]`

导出机器人配置。

**示例：**
```bash
# 输出到标准输出
tg-signer bot export my_channel

# 输出到文件
tg-signer bot export my_channel -o backup.json
```

### `tg-signer bot import <配置名> [-i 输入文件]`

导入机器人配置。

**示例：**
```bash
# 从文件导入
tg-signer bot import new_channel -i backup.json

# 从标准输入导入（输入JSON后按 Ctrl+D）
tg-signer bot import new_channel
```

## 配置示例

### 基本配置

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
    "enable_zhuzhen": true,
    "enable_wendao": true,
    "enable_yindao": true,
    "enable_yuanying": true,
    "enable_rift_explore": true
  },
  "star_observation": {
    "enabled": true,
    "default_star": "天雷星",
    "plate_count": 5,
    "sequence": ["天雷星", "烈阳星", "玄冰星"]
  },
  "herb_garden": {
    "enabled": false,
    "default_seed": "凝血草种子"
  },
  "xiaozhi_ai": {
    "authorized_users": [123456789],
    "filter_keywords": [],
    "blacklist_users": [],
    "trigger_keywords": ["@小智", "小智AI", "xiaozhi"],
    "response_prefix": "小智AI回复: ",
    "debug": false
  },
  "activity": {
    "enabled": true,
    "rules_extra": []
  }
}
```

## 模块功能

### 1. 每日例行任务 (DailyRoutine)

**功能：**
- 宗门点卯：每日自动点卯
- 宗门传功：每日最多3次自动传功
- 每日问安：每日问安增加情缘

**配置：**
```json
{
  "daily": {
    "enable_sign_in": true,
    "enable_transmission": true,
    "enable_greeting": false
  }
}
```

### 2. 周期任务 (PeriodicTasks)

**功能：**
- 闭关修炼（16分钟冷却）
- 引道（12小时冷却）
- 启阵（12小时冷却）
- 问道（12小时冷却）
- 探寻裂缝（12小时冷却）

**配置：**
```json
{
  "periodic": {
    "enable_qizhen": true,
    "enable_zhuzhen": true,
    "enable_wendao": true,
    "enable_yindao": true,
    "enable_yuanying": true,
    "enable_rift_explore": true
  }
}
```

### 3. 观星台 (StarObservation)

**功能：**
- 自动安抚星辰
- 收集精华
- 按序列轮转牵引星辰

**配置：**
```json
{
  "star_observation": {
    "enabled": true,
    "default_star": "天雷星",
    "plate_count": 5,
    "sequence": ["天雷星", "烈阳星", "玄冰星"]
  }
}
```

### 4. 小药园 (HerbGarden)

**功能：**
- 自动扫描药园状态
- 自动维护（除虫、除草、浇水）
- 自动采药
- 自动播种
- 种子兑换（当种子不足时）

**配置：**
```json
{
  "herb_garden": {
    "enabled": true,
    "default_seed": "凝血草种子",
    "seeds": {
      "凝血草种子": {
        "maturity_hours": 6,
        "exchange_batch": 5,
        "exchange_command": ".兑换 凝血草种子 {count}"
      }
    }
  }
}
```

### 5. 元婴任务 (YuanYingTasks)

**功能：**
- 自动查询元婴状态
- 自动元婴出窍
- 基于 ETA 的智能调度

**配置：**
```json
{
  "periodic": {
    "enable_yuanying": true
  }
}
```

### 6. 活动管理器 (ActivityManager)

**功能：**
- 自动识别频道活动
- 支持的活动：
  - 魂魄献祭
  - 天机考验（AI答题）
  - 虚天殿问答（AI答题）
  - 洞府访客
  - 宗门拍卖
  - 修仙问答

**配置：**
```json
{
  "activity": {
    "enabled": true,
    "rules_extra": []
  }
}
```

### 7. 小智AI (XiaozhiClient)

**功能：**
- WebSocket 连接小智AI服务
- 自动重连（指数退避）
- 活动问答（总是启用）
- 聊天AI互动（通过 `--ai` 标志控制）

**配置：**

**机器人配置 (bot_configs/xxx.json)：**
```json
{
  "xiaozhi_ai": {
    "authorized_users": [123456789, 987654321],
    "filter_keywords": ["广告", "刷屏"],
    "blacklist_users": [],
    "trigger_keywords": ["@小智", "小智AI", "xiaozhi"],
    "response_prefix": "小智AI回复: ",
    "debug": false
  }
}
```

**小智配置 (config/config.json)：**
```json
{
  "SYSTEM_OPTIONS": {
    "NETWORK": {
      "WEBSOCKET_URL": "wss://api.tenclass.net/xiaozhi/v1/",
      "WEBSOCKET_ACCESS_TOKEN": "your-token-here"
    }
  },
  "TG_SIGNER": {
    "XIAOZHI_AI": {
      "enabled": true,
      "protocol_type": "websocket",
      "auto_reconnect": true,
      "max_reconnect_attempts": 5,
      "connect_timeout": 10
    }
  }
}
```

**注意：**
- `--ai` 标志只控制聊天消息的AI互动
- 活动问答（如天机考验）总是会使用小智AI，不受 `--ai` 标志影响
- 如果未安装 `websockets` 库，系统会降级到模拟模式

## 目录结构

```
.signer/                         # 工作目录（默认）
├── config/                      # 配置文件夹
│   ├── config.json             # 小智AI配置
│   └── efuse.json              # 设备信息
├── bot_configs/                 # 机器人配置
│   ├── example.json            # 示例配置
│   ├── my_channel.json         # 用户配置1
│   └── another_channel.json    # 用户配置2
├── bot_workdir/                 # 机器人工作目录
│   └── states/                 # 状态持久化
│       ├── daily_state.json
│       ├── periodic_state.json
│       ├── herb_state.json
│       ├── star_state.json
│       └── yuanying_state.json
├── .env                         # 环境变量（可选）
└── sessions/                    # Telegram 会话文件
    └── my_account.session
```

## 环境变量

可以通过 `.env` 文件或系统环境变量配置：

**方式一：使用 .env 文件（推荐）**

在项目根目录创建 `.env` 文件，**注意不要使用 `export` 关键字**：

```bash
# Telegram API 凭据
TG_API_ID=your_api_id
TG_API_HASH=your_api_hash

# 代理配置
TG_PROXY=socks5://127.0.0.1:7897

# Session String（可选，用于无文件会话）
TG_SESSION_STRING=your_session_string
```

**方式二：使用 shell 环境变量**

```bash
export TG_API_ID="your_api_id"
export TG_API_HASH="your_api_hash"
export TG_PROXY="socks5://127.0.0.1:7897"
```

**注意：** 推荐使用 `tg-signer bot init` 命令来配置这些环境变量。

## 常见问题

### Q: 如何获取频道的 chat_id？

A: 使用 `tg-signer -a 账号名 login` 登录后，会显示最近的对话列表，包括 chat_id。

### Q: --ai 标志的作用是什么？

A: 
- 不使用 `--ai`: 小智客户端会初始化并用于活动问答（如天机考验），但不会响应普通聊天消息
- 使用 `--ai`: 在活动问答的基础上，还会响应触发关键词的聊天消息

### Q: 如何查看机器人的运行状态？

A: 查看日志文件 `tg-signer.log`，或使用 `-l debug` 参数查看详细日志：
```bash
tg-signer -l debug -a 账号名 bot run 我的机器人 --ai
```

### Q: 小智AI连接失败怎么办？

A: 
1. 检查 `config/config.json` 中的 WEBSOCKET_URL 和 WEBSOCKET_ACCESS_TOKEN 是否正确
2. 检查网络连接和代理设置
3. 确认已安装 `websockets` 库：`pip install websockets`
4. 系统会自动降级到模拟模式，不影响其他功能

### Q: 如何同时运行多个机器人？

A: 为每个频道创建独立的配置文件，然后在不同的终端或使用进程管理工具运行：
```bash
# 终端1
tg-signer -a account1 bot run channel1 --ai

# 终端2
tg-signer -a account1 bot run channel2 --ai

# 或使用不同账号
tg-signer -a account2 bot run channel3 --ai
```

### Q: 配置更新后需要重启机器人吗？

A: 是的，配置文件的更改需要重启机器人才能生效。按 `Ctrl+C` 停止后重新运行即可。

## 最佳实践

1. **使用配置文件**: 尽量使用配置文件而不是环境变量，便于管理和备份

2. **定期备份配置**: 使用 `tg-signer bot export` 定期导出配置备份

3. **日志监控**: 定期检查 `tg-signer.log` 文件，及时发现问题

4. **逐步启用功能**: 初次使用时，建议先启用少量功能，稳定后再逐步启用其他模块

5. **使用进程管理**: 生产环境建议使用 `systemd`、`supervisor` 或 `screen` 等工具管理机器人进程

6. **安全性**: 
   - 不要将含有 API 凭据的配置文件提交到公共仓库
   - 定期更换访问令牌
   - 限制小智AI的授权用户列表

## 技术支持

如有问题，请：
1. 查看 `INTEGRATION_STATUS.md` 了解模块集成状态
2. 查看 `ARCHITECTURE.md` 了解系统架构
3. 提交 Issue 到 GitHub 仓库
