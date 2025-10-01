# 小智机器人使用指南

本指南详细介绍如何配置和使用 tg-signer 的频道自动化机器人功能。

## 快速开始

### 1. 安装

```bash
pip install -e .
pip install websockets  # WebSocket 支持
```

### 2. 初始化

```bash
# 初始化配置
tg-signer bot init

# 设置 API 凭证（环境变量或配置文件）
export TG_API_ID="your_api_id"
export TG_API_HASH="your_api_hash"

# 登录账号
tg-signer -a my_account login
```

### 3. 创建并运行脚本

```bash
# 创建脚本配置
tg-signer bot config my_script

# 运行脚本
tg-signer bot -a my_account run my_script

# 启用 AI 互动
tg-signer bot -a my_account run my_script --ai
```

## CLI 命令

### `tg-signer bot init`

智能初始化配置，创建必要的目录和默认配置文件。

### `tg-signer bot config <script_name>`

交互式配置频道自动化脚本。

### `tg-signer bot -a <account> run <script> [--ai]`

运行自动化脚本。

参数：
- `-a, --account`: 账号名称
- `<script>`: 脚本名称
- `--ai`: 启用小智 AI 互动

### `tg-signer bot list`

列出所有配置的脚本。

### `tg-signer bot doctor [script]`

检查配置和环境。

### `tg-signer bot export/import`

导出/导入脚本配置。

## 功能模块

### 每日例行任务

- 点卯（`.点卯`）
- 传功（`.传功`，自动3次）
- 问安（`.问安`）

### 周期任务

- 启阵（1小时）
- 助阵（1小时）
- 问道（2小时）
- 引道（2小时）
- 元婴（4小时）
- 裂缝探索（6小时）

### 观星台自动化

- 自动扫描（`.观星台`）
- 牵引星辰（星序列轮转）
- 收集精华
- 安抚星辰
- 智能调度（基于冷却时间）

### 小药园自动化

- 自动扫描（`.小药园`）
- 维护（除草/除虫/浇水）
- 采药（成熟时自动）
- 播种（空闲时自动）
- 种子兑换（不足时自动）

### 小智 AI

- WebSocket 实时通信
- 自动重连
- 授权用户白名单
- 关键词触发

## 配置示例

详见 `docs/CONFIGURATION.md`

## 故障排除

详见文档故障排除章节。

## 许可证

BSD-3-Clause
