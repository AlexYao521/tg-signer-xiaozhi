# 修仙机器人架构设计与开发规划 (v1.1)

> 本文档用于指导项目从零到完善的系统化重构与增量迭代。目标：模块清晰、职责单一、易扩展、支持多账号多频道、具备自恢复与良好可 observability。

> **🆕 更新说明 (v1.1)**: 
> - 已完成模块化重构，创建了7个独立功能模块
> - 新增详细的冷却规则文档和企业级改进建议
> - 更新了实现状态，标注已完成的模块
> 
> **📚 相关文档**:
> - [PROJECT_ARCHITECTURE.md](./PROJECT_ARCHITECTURE.md) - 完整的项目架构文档（推荐阅读）
> - [COOLDOWN_RULES.md](./COOLDOWN_RULES.md) - 冷却规则详细说明
> - [ENTERPRISE_TODO.md](./ENTERPRISE_TODO.md) - 企业级改进建议清单
> - [活动回复词.md](./活动回复词.md) - 活动响应规范

---
## 目录
- [1. 设计目标与范围](#1-设计目标与范围)
- [2. 关键非功能目标](#2-关键非功能目标)
- [3. 总体架构概览](#3-总体架构概览)
- [4. 模块划分与职责](#4-模块划分与职责)
  - [4.1 Core 调度与运行时](#41-core-调度与运行时)
  - [4.2 指令发送统一管控层](#42-指令发送统一管控层)
  - [4.3 DailyRoutine (每日例行)](#43-dailyroutine-每日例行)
  - [4.4 PeriodicRoutine (周期任务)](#44-periodicroutine-周期任务)
  - [4.5 StarObservation (星宫/观星台)](#45-starobservation-星宫观星台)
  - [4.6 ActivityManager (频道活动识别/应答)](#46-activitymanager-频道活动识别应答)
  - [4.7 AI Interaction (小智对话子系统)](#47-ai-interaction-小智对话子系统)
  - [4.8 Config Manager (统一配置层)](#48-config-manager-统一配置层)
  - [4.9 State Persistence (本地 JSON/SQLite 状态)](#49-state-persistence-本地-jsonsqlite-状态)
  - [4.10 Logging & Metrics](#410-logging--metrics)
  - [4.11 CLI / Console UX](#411-cli--console-ux)
  - [4.12 Error Handling & Resilience](#412-error-handling--resilience)
  - [4.13 安全 / 速率控制 / 限流](#413-安全--速率控制--限流)
  - [4.14 测试策略](#414-测试策略)
  - [4.15 Account & Session (登录与会话复用)](#415-account--session-登录与会话复用)
  - [4.16 HerbGarden (小药园自动化)](#416-herbgarden-小药园自动化)
- [5. 运行时数据流](#5-运行时数据流)
- [6. 配置体系设计](#6-配置体系设计)
- [7. 状态文件与数据结构](#7-状态文件与数据结构)
- [8. 并发 & 调度模型](#8-并发--调度模型)
- [9. 可观测性与排障](#9-可观测性与排障)
- [10. 扩展点与框架钩子](#10-扩展点与框架钩子)
- [11. 迭代路线与里程碑](#11-迭代路线与里程碑)
- [12. 任务 TODO Backlog](#12-任务-todo-backlog)
- [13. 风险与缓解](#13-风险与缓解)
- [14. 附录：命名与代码规范建议](#14-附录命名与代码规范建议)
- [15. 指令与响应规范](#15-指令与响应规范)

---
## 1. 设计目标与范围
| 目标 | 描述 |
|------|------|
| 模块化 | 各功能（每日/周期/星宫/AI/活动）独立，低耦合高内聚。|
| 可扩展 | 新玩法/指令可通过“策略类 + 回调”快速挂载。|
| 多账号 | 同目录多 session，状态文件按账号+频道 namespacing。|
| 可靠性 | 崩溃后可基于状态文件恢复进度，不重复执行已完成任务。|
| 透明调试 | 日志分层、关键动作审计、失败重试可追溯。|
| 安全 | 速率限制、黑/白名单、AI 输入清洗。|
| 国内容灾 | 设计连接自愈、指数回退、轻量告警。|
| 低侵入测试 | 每个子系统拥有单元/集成测试入口。|
| 登录体系复用 | Telegram 登录 / session 存储完全沿用现有 tg-signer 机制，不改存储格式与兼容行为。|

## 2. 关键非功能目标
- 启动时间 < 5s（缓存配置 + 延迟初始化）
- 内存常驻 < 150MB（无大批量消息缓存）
- 单指令平均发送间隔遵守频道限速（10~15 秒随机）
- 发送触发tg慢模式 等待几秒重试
- 重连自愈：在 2 min 内恢复 > 90% 场景
- 日志行可 grep：包含明确 TAG 前缀

## 3. 总体架构概览
```
+---------------- CLI / Console ----------------+
|  parse args / help / profile selection       |
+---------------------+------------------------+
                      v
            +--------------------+
            |  XiuXianBot (Core) |  <== 事件循环 / 生命周期
            +----------+---------+
                       | orchestrates
   +---------+---------+----------+-----------+-----------+
   v         v                    v           v           v
 Daily   Periodic   StarObservation    ActivityMgr    AIInteraction
 Routines  Jobs      (观星/安抚/牵引/收集)  (活动解析)    (小智WS/MQTT)
   |         |             |                 |            |
   +---------+-------------+-----------------+------------+
                     v
              Command Queue (优先级小顶堆 + 去重 + 速率控制)
                     v
                Telegram Client Adapter
                     v
               Telegram Network (Pyrogram)
```

## 4. 模块划分与职责

> **📊 实现状态 (Implementation Status)**
> - ✅ **已完成**: 模块已实现并通过测试
> - 🚧 **进行中**: 模块正在开发
> - 📝 **计划中**: 待实现的模块
> 
> | 模块 | 状态 | 文件 | 说明 |
> |-----|------|------|------|
> | Core 调度与运行时 | 🚧 | `bot_worker.py` | 部分实现，需集成新模块 |
> | DailyRoutine | ✅ | `daily_routine.py` | 已完成，154行 |
> | PeriodicRoutine | ✅ | `periodic_tasks.py` | 已完成，175行 |
> | StarObservation | ✅ | `star_observation.py` | 已完成，285行 |
> | HerbGarden | ✅ | `herb_garden.py` | 已完成，329行 |
> | ActivityManager | ✅ | `activity_manager.py` | 已完成，252行 |
> | Cooldown Parser | ✅ | `cooldown_parser.py` | 已完成，124行，45个测试 |
> | Cooldown Config | ✅ | `cooldown_config.py` | 已完成，118行 |
> | Logging | ✅ | `logger.py` | 已增强，支持按账号分离 |
> | Config Manager | ✅ | `bot_config.py` | 已存在 |
> | State Persistence | ✅ | `bot_worker.py` | StateStore已实现 |
> | AI Interaction | ✅ | `xiaozhi_client.py` | 已存在 |

### 4.1 Core 调度与运行时
- 负责初始化、启动、停止、重连、自愈、任务队列主循环。
- 提供通用：`enqueue_command`, 速率控制, 回调执行, 去重键策略。

### 4.2 指令发送统一管控层
- 防止不同功能并发直接调用 send_message。
- 统一：慢速模式处理 / 重试 / 网络超时 / 语义日志 / reply_to 透传。
- 提供 hook: `before_send`, `after_send`, `on_retry`（便于 metrics 注入）。

### 4.3 DailyRoutine (每日例行)
- 点卯 / 问安 / 传功三元流程。
- 被动解析补偿（监听频道消息时标记完成）。
- 状态字段：`sign_in_done`, `greeting_done`, `transmission_count`, `last_message_id`。
- 午夜刷新：定时任务 + 重置日度数据。

### 4.4 PeriodicRoutine (周期任务)
- .启阵 / .助阵 / .问道 / .引道 / .元婴状态。
- 新增：`.探寻裂缝`（空间裂缝探索，基础冷却 12 小时）。
  - 成功或失败（风暴受创）都进入冷却。
  - 若返回文本包含 “请在 X小时Y分钟Z秒 后再行探寻” 解析精确秒数；否则回退默认 12h。
  - 失败（风暴/受创）提前 5~10 分钟前置预热探测：在冷却结束前 5~10 分钟再排一次 .探寻裂缝 以抵消慢速模式延迟。
- 冷却解析统一复用 `_extract_cooldown_seconds`；最低保障阈值 > 10 分钟，否则视为解析失败走默认。

### 4.5 StarObservation (星宫/观星台)
- 功能：`.观星台` -> 判断：可收集 / 空闲 -> `.收集精华` / `.牵引星辰 <星名>` / `.安抚星辰`。
- 星序列轮转：配置 `sequence`；为空时全用 default 星。
- 冷却/躁动/频率限制策略：指数回退 + 抖动。
- 状态：`last_pacify_ts`, `sequence_index`, 去重计划。

### 4.6 ActivityManager (频道活动识别/应答)
- 关键词/模式：问答、魂魄献祭、洞府访客等。
- 提供插件式匹配：`ActivityRule {pattern, cooldown, on_match}`。
- 可扩展持久化回答库（json + 热加载）。

### 4.7 AI Interaction (小智对话子系统)
- 通过 WebSocket / MQTT 双通道（配置集中管理）。
- 授权策略：白名单 / 开放 + 黑名单过滤。
- 文本过滤：低语义 / 纯标点 / 纯数字 / token 噪声。
- 流式聚合模式：首段发送 -> 后续片段 edit，同步减负速率。
- 自愈：断线指数退避重连。

### 4.8 Config Manager (统一配置层)
- 结构层次：
  1. 默认内建值 (hard-coded defaults)  
  2. 全局配置 (global.json 可选)  
  3. 账号/宗门配置 `{sect}.json`  
  4. 环境变量 / CLI 参数覆盖 (最高)
- 解析：宽松布尔 / 去注释 / 去尾逗号 / 容错日志。

### 4.9 State Persistence (本地 JSON/SQLite 状态)
- 尽量 JSON，避免锁争用：`daily_state.json`, `periodic_state.json`, `star_state.json`。
- 统一写入工具：`StateStore`（支持 atomic write + 异常回退）。
- 命名：`acct_<account>_chat_<chat_id>` 顶层键，兼容旧格式。

### 4.10 Logging & Metrics
- 分层 TAG：`[启动] [队列] [每日] [周期] [星宫] [对话] [活动] [错误] [网络]`。
- 可选 JSON 行日志（写文件）+ 人类可读（stdout）。
- 指标（后续可选）：发送成功率 / 重试次数 / 平均冷却解析时长。

### 4.11 CLI / Console UX
- 子命令：`login`, `list-sects`, `run <sect>`, `config create <sect>`, `doctor`, `help`。
- 错误友好提示：频道无效 / 会话被踢 / 配置解析失败 / 速率限制原因。
- `doctor`：检查：网络、session 完整性、配置字段缺失。

### 4.12 Error Handling & Resilience
- 分类：可重试（网络/慢速）、致命（配置缺失）、业务（关键词未匹配）。
- 重试策略：指数 + 抖动 + 上限；失败告警点打印 root cause。
- 停止流程：`stop()` 置位 + 队列收尾 + 取消后台任务。

### 4.13 安全 / 速率控制 / 限流
- 统一 min send interval + 任务优先级（重要指令 > AI 回复）。
- AI 输入清洗：替换 '.' -> 空格；去 @用户名；过滤粗短噪声。
- 黑名单：用户 ID/用户名；白名单模式 -> 未列入拒绝。
- 防刷：用户 -> 上次对话时间戳; 星宫安抚最小间隔。

### 4.14 测试策略
| 层级 | 示例 | 工具 |
|------|------|------|
| 单元 | 冷却解析 `_extract_cooldown_seconds` | pytest |
| 单元 | 观星台决策（文本->动作） | pytest parametrize |
| 单元 | 配置宽松解析 | pytest |
| 集成 | 队列优先级与去重 | pytest + fake clock |
| 集成 | Daily + 被动补偿 | 频道消息模拟 | 
| 集成 | AI 流式聚合 | mock AI client |
| 冒烟 | CLI run / stop 正常退出 | tox |

### 4.15 Account & Session (登录与会话复用)
**决策**：复用 tg-signer 现有账号登录与会话文件体系，不做结构性改动，保持所有已有 `*.session` 与 `*.session_string` 文件向后兼容。

**原因**：
- 现有会话格式由 Pyrogram 管理，稳定且已通过生产验证。
- 自定义封装将引入额外维护成本与潜在兼容风险（例如 Telegram 协议升级）。
- 多账号并行已经通过独立 session 文件天然隔离，无需再造轮子。

**现状复述**：
- 会话文件命名：`<account>.session` / `<account>.session_string`（可选）位于工程根或指定工作目录。
- 不改变加密/序列化方式；仍由 Pyrogram 内部读写。
- 账号切换：CLI 通过 `-a/--account` 指定，直接选择对应会话文件。
- 首次登录（需要验证码/密码）流程保持原交互，不自动化脚本化，以降低被封风险。

**与本架构的融合**：
- Core 初始化时只负责调用 `get_client(account=...)`，不包裹登录逻辑。
- 状态文件命名空间使用：`acct_<account>_chat_<chat_id>`；不把 session 数据混入业务状态 JSON。
- 若未来需要“纯内存运行模式”，可通过可选参数 `in_memory=True` 创建临时会话（当前不默认启用）。

**安全建议**：
- 不提交 `*.session` 到版本库（`.gitignore` 已覆盖，如无则补充）。
- 若使用 `session_string`，建议通过环境变量注入，避免平铺在配置 JSON。
- 避免将会话文件复制到不受控的共享目录（防止被复用劫持）。

**后续增强（暂不实施）**：
- 失败登录重试统计（可在 doctor 中附带简报）。
- 账号健康巡检：最近一次成功 API 调用时间戳。
- 只读模式：提供 `--readonly-session` 防止意外写回（调试场景）。

### 4.16 HerbGarden (小药园自动化)
小药园为独立自动化子系统，核心流程：扫描 -> 解析多块灵田状态 -> 计划维护指令 -> 收获 -> 播种补货 -> 再次扫描。

#### 4.16.1 灵田状态机
| 状态 | 频道展示示例 | 动作 | 优先级 | 备注                                      |
|------|--------------|------|--------|-----------------------------------------|
| 已成熟 ✨ | `已成熟` | `.采药` (一键) | P1 | 一键采药涵盖所有成熟地块；成功后这些地块进入“空闲”              |
| 害虫侵扰 🐛 | `害虫侵扰` | `.除虫` | P0 | 没有防止产量衰减机制（如有害虫侵扰 采药前必须除虫而已）            |
| 杂草横生 🌿 | `杂草横生` | `.除草` | P0 | 没有防止产量衰减机制（如有杂草横生 采药前必须除草而已）                                     |
| 灵气干涸 🍂 | `灵气干涸` | `.浇水` | P0 | 没有防止产量衰减机制（如有灵气干涸 采药前必须浇水而已）                             |
| 生长中 🌱 | `生长中 (剩余: 17分钟12秒)` | 记录成熟 ETA | P2 | 到达 ETA 前不操作；到 ETA - 随机抖动 1~2 分钟重新`.小药园` |
| 空闲 | `空闲` | `.播种 <地块> <种子>` | P1 | 种子不足则先 `.兑换`                            |
| 冷却/占用 | “播下” / “正在冷却” | 跳过 | P3 | 日志跟踪                                    |

> 一键类指令（除草/除虫/浇水/采药）若频道为**多块**匹配，会统一返回 “一键XX完成！”。返回 “没有需要【XX】” 时撤销同类未执行计划。

#### 4.16.2 指令规划顺序
1. 解析扫描 `.小药园` 回复 -> 构建结构体：`plots = [{idx, state, eta?, seed?}]`。
2. 维护动作聚合：除虫/除草/浇水 各自判断是否存在 ≥1 目标地块；存在则入队（去重键 `herb:action:<type>:<chat>`）。
3. 若存在成熟 -> `.采药` 入队；采药成功回调：标记相关地块 -> 进入空闲 -> 触发播种流水。
4. 播种：统计空闲地块数 N；检查种子库存（内存状态 + 持久化 state）。
   - 若库存 < N：入队 `.兑换 <种子> N`（或按配置批量阈值）。
   - 兑换成功回调 -> 生成 N 条 `.播种 idx 种子`（可选择短随机延迟与一键播种是否存在视后续玩法确认）。
5. 生长中：解析剩余时间 (小时/分钟/秒) -> 记录最早成熟时间 earliest_mature_ts；调度下一轮 `.小药园` = earliest_mature_ts - jitter(60~120s)。
6. 所有操作完成后如仍有地块在生长，设置保底巡检：`max(earliest_mature_ts - 120s, now+1800s)`，防止错过成长异常。

#### 4.16.3 配置结构 (新增 `herb_garden` 节点)
```jsonc
"herb_garden": {
  "enabled": true,
  "default_seed": "凝血草种子",
  "seeds": {
    "凝血草种子": { "maturity_hours": 6, "exchange_batch": 5, "exchange_command": ".兑换 凝血草种子 {count}" },
    "清灵草种子": { "maturity_hours": 8, "exchange_batch": 5, "exchange_command": ".兑换 清灵草种子 {count}" }
  },
  "scan_interval_min": 900,        // 无 ETA 时的兜底扫描(秒)
  "post_maintenance_rescan": 30,    // 一键维护后二次扫描延迟
  "post_harvest_rescan": 20,        // 采药后快速再扫描
  "seed_shortage_retry": 600        // 兑换失败(缺贡献等)后重试间隔
}
```

#### 4.16.4 持久化字段
`herb_garden_state.json` (命名空间同前) 中每账号+频道：
```jsonc
{
  "acct_<a>_chat_<c>": {
    "plots": [
      {"idx":1,"seed":"凝血草种子","state":"growing","mature_ts":1730450000},
      {"idx":2,"seed":"凝血草种子","state":"pest"},
      {"idx":3,"seed":null,"state":"idle"}
    ],
    "seed_inventory": {"凝血草种子": 3, "清灵草种子": 0},
    "sequence_seed_index": 0,          // 若未来支持轮播不同种子
    "next_scan_ts": 1730448000,
    "last_full_harvest_ts": 1730441000
  }
}
```

#### 4.16.5 解析要点
- 逐行解析：匹配 `^(\d+)号灵田: (.+?) - (.+)$`。
- 状态映射：
  - `已成熟` -> mature
  - `害虫侵扰` -> pest
  - `杂草横生` -> weed
  - `灵气干涸` -> dry
  - `生长中` -> growing + 剩余 `X小时Y分钟Z秒` -> 计算 `mature_ts` = now + secs
  - `空闲` -> idle
  - 其余 / 未识别 -> unknown (日志标记)
- 成熟 ETA 解析失败：回退 maturity_hours（来自 seed 配置） + 2 分钟容错。

#### 4.16.6 调度策略摘要
| 事件 | 下一步调度 |
|------|------------|
| 初次启用 | 5s 后 `.小药园` |
| 一键维护成功 | `post_maintenance_rescan` 后再 `.小药园` |
| 采药成功 | `post_harvest_rescan` 后再 `.小药园` |
| 兑换成功 | 3~6s 后连续 `.播种` 各空闲地块；播种完 15~25s 后 `.小药园` |
| 播种失败(无种/冷却) | 记录失败原因 -> `seed_shortage_retry` 后重试兑换或放弃一轮 |
| growing 解析 | earliest_mature_ts - (60~120s 随机) |
| 无任何活跃地块 (全部 idle) | 依据默认种子立即播种流水 / 若库存不足则兑换 |
| 无 ETA 且无任务 | `scan_interval_min` 作为兜底 |

#### 4.16.7 去重键建议
| 动作 | 去重键格式 |
|------|-------------|
| 扫描 | `herb:scan:<chat>` |
| 维护(除草/除虫/浇水) | `herb:maint:<type>:<chat>` |
| 采药 | `herb:harvest:<chat>` |
| 播种单地块 | `herb:plant:<chat>:<idx>` |
| 兑换 | `herb:exchange:<seed>:<chat>` |

#### 4.16.8 失败与回退
| 场景 | 处理 |
|------|------|
| 采药返回“没有需要【采药】” | 取消后续播种链条，立即重扫以同步状态 |
| 维护返回“没有需要【除草】” | 清除 pending 维护计划，继续其它维护类型 |
| 兑换失败（背包无贡献） | 打印告警，记录冷却，`seed_shortage_retry` 后重试；超过 N 次放弃当日自动播种 |
| 播种返回“播下” | 标记该地块为 growing (无 ETA)，等待下一次 `.小药园` 填充 ETA |
| ETA 已过 + 未成熟 | 强制立即 `.小药园` 重扫 + 记录告警计数 |

#### 4.16.9 与星宫模块差异
| 维度 | 星宫 | 小药园 |
|------|------|--------|
| 扫描指令 | `.观星台` | `.小药园` |
| 一键维护 | `.安抚星辰` | `.除草` / `.除虫` / `.浇水` / `.采药` |
| 序列机制 | 星序列 | 种子轮播 (可选) |
| ETA 来源 | 冷却文本 or 内部冷却估算 | 文本剩余时间 or maturity_hours |
| 缺料处理 | 无 | 自动 `.兑换` 种子 |

---
## 5. 运行时数据流
1. CLI 解析 -> 载入 sect 配置 -> 初始化 Core。  
2. Core 启动 Pyrogram，缓存 me info。  
3. 注册监听回调 -> 接收消息 -> 按序：每日补偿 -> 星宫解析 -> 活动解析 -> AI交互。  
4. 功能模块通过 `enqueue_command()` 统一入队。  
5. 队列调度器：按 when_ts + priority 取出 -> 速率控制 -> Telegram 发送 -> 等待回复（可选） -> 回调 -> 再次调度链。  
6. 状态变更写入对应 JSON。  

---
## 6. 配置体系设计
示例 `sect_a.json`（新增 herb_garden & rift_explore 标志）：
```jsonc
{
  "chat_id": -1001234567890,
  "daily": { "enable_sign_in": true, "enable_transmission": true, "enable_greeting": false },
  "periodic": { "enable_qizhen": true, "enable_zhuzhen": true, "enable_wendao": true, "enable_yindao": true, "enable_yuanying": true, "enable_rift_explore": true },
  "star_observation": { "enabled": true, "default_star": "天雷星", "plate_count": 5, "sequence": ["天雷星", "烈阳星", "玄冰星"] },
  "herb_garden": { "enabled": true, "default_seed": "凝血草种子", "seeds": { "凝血草种子": {"maturity_hours": 6, "exchange_batch": 5, "exchange_command": ".兑换 凝血草种子 {count}" }, "清灵草种子": {"maturity_hours": 8, "exchange_batch": 5, "exchange_command": ".兑换 清灵草种子 {count}" } }, "scan_interval_min": 900, "post_maintenance_rescan": 30, "post_harvest_rescan": 20, "seed_shortage_retry": 600 },
  "xiaozhi_ai": { "authorized_users": [12345678], "filter_keywords": ["广告", "刷屏"], "blacklist_users": [], "debug": false },
  "activity": { "enabled": true, "rules_extra": [] }
}
```

---
## 7. 状态文件与数据结构
| 文件 | 说明 | 关键结构 |
|------|------|----------|
| `daily_state.json` | 点卯/问安/传功 | `{ "acct_<a>_chat_<c>": {"sign_in_done": true, ...}}` |
| `periodic_state.json` | 各周期任务下次时间 (含裂缝) | `{ "acct_<a>_chat_<c>": {"qizhen": ts, "rift_explore": ts}}` |
| `star_state.json` | 观星台 | `{ "acct_<a>_chat_<c>": {"sequence_index":1, ...}}` |
| `herb_garden_state.json` | 小药园 | `{ "acct_<a>_chat_<c>": {"plots":[],"seed_inventory":{},"next_scan_ts":ts}}` |
| `activity_cache.json` | 活动冷却 | `{ "rule_key": last_ts }` |
| `ai_recent.json` (可选) | 去重窗口 | `{ "recent": [ ... ] }` |

---
## 8. 并发 & 调度模型
| 元素 | 描述 |
|------|------|
| asyncio loop | 单主循环，所有 I/O 协程化。|
| Queue 调度 | 小顶堆 (when_ts, priority, order)；order 解决相同时间同优先级稳定性。|
| 速率控制 | 全局 `_send_lock` + `min_send_interval + jitter`。|
| 后台任务 | AI 连接监控 / 午夜刷新 / 周期任务延迟调度。|
| 取消策略 | `stop()` -> set event -> 各 await 检测退出。|
| 回调链 | 指令 -> 等待回复 -> 回调 -> 再入队（形成自循环）。|

潜在阻塞点：
- 历史消息轮询过慢 -> 需要指数退避 + 超时重连。
- 同时大量模块重排任务 -> 需去重键控制。

---
## 9. 可观测性与排障
| 类别 | 实现 |
|------|------|
| 日志 | stdout 人类可读 + file JSON 行日志 (`/logs/<date>.log`) |
| 事件审计 | 指令发送/重试/失败/回调结果记录 JSON 行。|
| 健康检查 (CLI) | `doctor`：检测配置字段、会话文件是否存在、网络连通性 (对 Telegram API ping)。|
| 统计 (后续) | 简易累积器 -> 定期 flush (发送次数、成功率)。|
| 报警 (可选) | 错误>阈值写入一个 `alerts.log`。|

---
## 10. 扩展点与框架钩子
| Hook | 目的 | 形态 |
|------|------|------|
| `before_send(command)` | 修改/拒绝发送 | 可同步/异步 |
| `after_send(command, message)` | 统计/日志 | 异步 |
| `on_activity_match(rule, message)` | 活动自定义逻辑 | 异步 |
| `register_periodic_custom(key, cmd, parse_fn)` | 新周期任务 | API |
| `ai_preprocess(user_id, text)` | 自定义过滤 | 返回(accept, new_text) |

---
## 11. 迭代路线与里程碑
| Milestone | 内容 | 输出 |
|-----------|------|------|
| M0 基线 | 抽离架构骨架/文档 | 本文档 + 骨架目录 |
| M1 队列稳定 | 统一调度/发送/速率/重试 | 队列模块 + 单测 |
| M2 Daily & Periodic | 日常+周期任务可恢复 | 状态文件 + 测试 |
| M3 星宫核心 | 观星/牵引/收集/安抚 | Star 模块 + 文档 |
| M4 活动系统 | 插件化匹配与冷却 | ActivityManager 重构 |
| M5 AI 集成 | 流式/断线自愈/过滤 | AI 客户端适配层 |
| M6 CLI 优化 | help/doctor/config scaffold | CLI 子命令完善 |
| M7 Observability | JSON 日志/统计/故障注记 | 统一 logger + metrics |
| M8 强健化 | 压测/边界/回归 | 性能与异常策略 |

---
## 12. 任务 TODO Backlog
优先级：P0(立即) P1(短期) P2(增强) P3(可选增值)

| ID | P | 模块 | 任务 | 描述 / 验收标准 |
|----|---|------|------|------------------|
| 1 | P0 | Parsing | 统一消息分类管线 | 实现 `classify_message()`：按顺序 Daily->Star->Herb->Periodic->YuanYing->Activity->AI；单元测试至少 12 例覆盖多场景 |
| 2 | P0 | Cooldown | `_extract_cooldown_seconds` 改进 | 支持 “X小时Y分钟Z秒” / “Y分钟Z秒” / “Z秒”；解析失败回退默认；含模糊空格与全角字符容错 |
| 3 | P0 | Daily | 传功回复校验与 reply 逻辑 | 检测需回复错误提示后记录 `last_message_id`；完成 3/3 后不再入队；单测覆盖成功/未回复/超过次数 |
| 4 | P1 | Star | `.观星台` 行解析器 | 解析引星盘编号/星名/状态/剩余时间；测试：成熟/凝聚中/空闲/精华已成 全覆盖 |
| 5 | P1 | Herb | `.小药园` 行解析器 | 解析 6 种状态+剩余时间；成熟后播种链；加入失败回退策略测试 |
| 6 | P1 | YuanYing | `.元婴状态` 解析 | 识别出窍/归来倒计时/可出窍；自动调度 `.元婴出窍`；添加 3 种典型文本测试 |
| 7 | P1 | Periodic | 裂缝预热调度 | 风暴/失败冷却结束前 5-10min 安排预热；单测伪造时间快速前推验证 |
| 8 | P2 | Logging | 发送-响应审计 | JSON 行包括 command, message_id, parse_result, latency_ms |
| 9 | P2 | Resilience | 响应超时补偿 | 90s 无响应 -> 标记 pending 响应失败 -> 冷却使用默认，写 WARNING |
| 10 | P2 | Rate | Jitter 策略配置化 | 支持配置 `min_interval`, `max_interval`；随机分布测试不偏离期望均值 |
| 11 | P3 | Metrics | 简易指标导出 | 内存累积器 -> 定期日志 flush；统计 success/fail/timeout |
| 12 | P3 | Activity | 插件热加载 | 监测配置文件 mtime 变化自动重载规则 |

---
## 13. 风险与缓解
| 风险 | 描述 | 等级 | 缓解措施 |
|------|------|------|----------|
| 文本格式变动 | 游戏返回文案小改导致正则失效 | 高 | 使用多模式 regex + 容错分支；记录未匹配样本日志收集 |
| 冷却误判 | 解析错导致过早发送触发慢速 | 高 | 下限阈值 (>=10 分钟)；过短结果回退默认；引入 parse_score |
| 竞争去重缺失 | 多模块同时排相同指令 | 中 | 去重键统一生成函数 + 单测覆盖冲突 |
| 状态文件损坏 | 非原子写入中断 | 中 | 临时文件 + rename；损坏时自动备份并重建 |
| 多账号放大速率 | 聚合发送超出 Telegram 限制 | 中 | 账号内限速 + 全局节流器，可配置并行账户限制 |
| 夜间跨日刷新 | 午夜前后状态未及时重置 | 中 | 每日 00:05 定时刷新 + 手动命令触发补偿 |
| AI 噪声干扰解析 | AI 回复与游戏系统消息混淆 | 低 | 消息来源过滤：只解析系统机器人 user_id 白名单 |
| 长时间断线 | 网络波动导致任务积压 | 中 | 断线队列不清空；重连后立即刷新 `.观星台` / `.小药园` / `.元婴状态` |
| 种子/资源不足流程死循环 | 兑换失败持续重试 | 低 | 计数上限 + 当日熔断标记 `seed_exchange_disabled=true` |

---
## 14. 附录命名与代码规范建议
- Python: 模块 `snake_case`, 类名 `PascalCase`, 常量大写。
- 去重键：`<domain>:<action>[ :<sub>]*:<chat>`；避免含空格与中文。
- 状态键：`acct_<account>_chat_<chat_id>` 顶层；内部字段英文 snake_case；必要时加 `*_ts` 秒级时间戳。
- Regex 常量前缀：`RE_`，集中放置于各模块 `patterns.py` 或模块文件顶部，附示例注释。
- 日志 TAG 采用方括号前缀：`[每日]` `[星宫]` `[药园]` `[周期]` `[队列]`；错误统一 `[错误]`。
- 函数返回解析结果统一使用 `ParseResult` 数据类：`{matched: bool, type: str, payload: dict, cooldown_s?: int, next_actions?: list[str]}`。
- 复杂调度入口函数添加 3 行“契约注释”：输入/副作用/失败策略。
- 代码行宽建议 <= 110；中文注释短句不赘述。

---
## 15. 指令与响应规范
本节整合《指令和响应说明.md》并将文本格式固化为可解析规则，用于：
1. 统一解析：将频道文本 -> 结构化事件。
2. 统一冷却：提取下一次执行时间与预热时间。
3. 统一调度：映射到去重键与优先级。
4. 统一回退：解析失败走安全默认。

### 15.1 分类顺序 (Pipeline)
Daily(SignIn/Greeting/Transmission) -> Star(观星台/收集/牵引/安抚) -> Herb(小药园/维护/播种/采药/兑换) -> Periodic(闭关/引道/问道/裂缝/启阵/助阵) -> YuanYing(元婴状态/出窍) -> Activity(规则匹配) -> AI(普通对话)。
分类一旦命中（`matched=True`）即停止继续下游解析（除非标记 `allow_chaining` 的特殊活动规则）。

### 15.2 通用解析原则
- 正则多模式：优先全量匹配，其次宽松匹配（去除空格/中文标点）。
- 数值提取：统一使用非贪婪组 `(\d+)`，允许中间出现全角空格。
- 冷却解析：
  - 模式：`(?:(\d+)小时)?(?:(\d+)分钟)?(?:(\d+)秒)?`，空缺视为 0。
  - 结果秒数 < 600 (10 分钟) 且原指令默认冷却 > 1h 时判定异常 -> 使用默认。
- 失败/已完成识别：包含关键词“已点卯 / 今日已 / 已经 / 没有需要 / 正在运转 / 无法 / 不可 / 尚未”。
- 时间戳：所有冷却基准使用解析完成时刻 `now()`；调度加入随机抖动 `± jitter_pct (默认5%)` 上限不超过 2 分钟。
- 去重：同一 logical 行为在冷却窗口内生成相同去重键；重复 enqueue 被丢弃并记录 debug。

### 15.3 Daily 模块
| 指令 | 成功匹配关键字 | 已完成/失败关键词 | 默认冷却 | 去重键 | 备注 |
|------|---------------|------------------|----------|--------|------|
| `.宗门点卯` | `点卯成功` | `今日已点卯` | 24h | `daily:signin:<chat>` | 午夜刷新后可再次 |
| `.每日问安` | `情缘增加` | `今日已经问安` | 24h | `daily:greet:<chat>` | 可配置是否启用 |
| `.宗门传功` | `今日已传功 3/3` | `请明日再来` / `需回复` | 30s (尝试间隔) | `daily:transmit:<chat>` | 需 reply 最近自己消息；维护 `transmission_count` |

传功逻辑：
1. 未达到 3 次 -> 发送 `.宗门传功`（若需要 reply 缺失 -> 记录提示 -> 等待新自发言后再补）。
2. 匹配到 “今日已传功 X/3” -> `transmission_count=X`；X<3 冷却 30~45s；X=3 停止当日。

### 15.4 Periodic / 循环任务
| 指令 | 文案成功锚点 | 冷却提取模式示例 | 默认冷却 | 去重键 | 预热策略 |
|------|--------------|------------------|----------|--------|----------|
| `.闭关修炼` | `闭关成功` | `需要打坐调息 (?P<cd>.+?) 方可` | 16m | `periodic:biguan:<chat>` | 无 |
| (闭关阻塞) | `灵气尚未平复` | `请在 (?P<cd>.+?) 后再试` | 16m | 同上 | 无 |
| `.引道 水` | `你引动` | `请在 (?P<cd>.+?) 后再次引道` | 12h | `periodic:yindao:<chat>` | 无 |
| `.问道` | `问道`/`天机不可频繁窥探` | `请在 (?P<cd>.+?) 后再来问道` | 12h | `periodic:wendao:<chat>` | 无 |
| `.探寻裂缝` | `探寻成功`/`遭遇风暴` | `请在 (?P<cd>.+?) 后再行探寻` | 12h | `periodic:rift:<chat>` | 结束前 5~10min 预热扫描 |
| `.启阵` | (待补锚点) | (同通用) | 8h | `periodic:qizhen:<chat>` | 无 |
| `.助阵` | (待补锚点) | (同通用) | 8h | `periodic:zhuzhen:<chat>` | 无 |
| `.元婴状态` | `你的本命元婴` | `归来倒计时: (?P<cd>.+?)` | 30m (查询频率) | `yuanying:status:<chat>` | 可出窍立即排 `.元婴出窍` |
| `.元婴出窍` | `云游 8 小时` | （不适用） | 8h | `yuanying:chuxiao:<chat>` | 结束前 2min 预扫 |

解析到风暴/受创：仍然使用解析出来的新冷却；若无冷却文本 -> 默认 12h。

### 15.5 星宫 (观星台)
`.观星台` 回复行解析：`^(?P<idx>\d+)号引星盘: (?P<star>[^ -]+) - (?P<state>.+?)(?: \(剩余: (?P<remain>.+?)\))?$`

启动优先策略：始终先尝试发送 `.安抚星辰`（P0）。原因：安抚指令可直接返回“没有需要安抚的星辰”且无需先扫描；若存在躁动/星光黯淡状态则立即处理，减少精华损失窗口。安抚结果处理：
- 成功（含“成功安抚”）-> 5~8s 后排 `.观星台` 刷新状态。
- 无需要（含“没有需要安抚”/“没有需要”）-> 2~4s 后排 `.观星台`。
- 失败/网络异常 -> 指数退避 15~30s 重试，超过 N 次(默认3) 降级直接 `.观星台`。

| 状态标签 | 内部 state | 后续动作 | 优先级 | 去重键 |
|----------|-----------|----------|--------|--------|
| `精华已成` | ready | `.收集精华` | P0 | `star:collect:<chat>` |
| `空闲` | idle | `.牵引星辰 <idx> <nextStar>` | P1 | `star:pull:<chat>:<idx>` |
| `凝聚中` | condensing | (等待) | P2 | `star:wait:<chat>:<idx>` |
| `星光黯淡` / `元磁紊乱` | agitated | `.安抚星辰` (若未先发送) | P0 | `star:pacify:<chat>` |

收集成功 -> 3~6s 后排 `.观星台`；安抚成功(若是启动第一步) -> 已在启动策略中处理；牵引成功 -> 记录 star -> 等待凝聚（解析 ETA 再安排下一次 `.观星台`）。

解析兼容：`agitated` 识别同时匹配“星光黯淡”、“躁动”、“狂暴” 关键字；未来若词汇更改统一加入同义表。

### 15.6 小药园 (与 4.16 补充一致)
解析与动作顺序：维护(P0) -> 采药(P1) -> 播种(P1) -> 等待(P2)。播种链需在采药成功后再生成，避免资源浪费。
关键响应锚点：
- 一键维护成功：“一键(除草|除虫|浇水)完成” -> 清空对应 pending。
- 未匹配维护：“没有需要【除草】” 等 -> 移除该动作计划。
- 采药：“一键采药完成” -> 所有 mature -> idle。
- 播种成功：“播下” -> 设置 growing 无 ETA；等待下一次 `.小药园` 填充 ETA。
- 兑换成功：“兑换成功” -> 更新库存。

### 15.7 元婴 (出窍 / 状态)
`状态: 元神出窍` -> 提取剩余归来倒计时；归来 < 10 分钟时增加 2 分钟预扫以确保结算。
`状态: 窍中温养` 且检测到上一轮未出窍或冷却结束 -> 立即排 `.元婴出窍`。
`【元神归窍】` 块出现 -> 奖励结算：清除出窍中标记 -> 30~45s 后调度 `.元婴出窍`（若配置启用自动出）。

### 15.8 去重键与优先级统一规范
| 行为类型 | 去重键格式 | 优先级建议 | 说明 |
|----------|-----------|-----------|------|
| Daily | `daily:<type>:<chat>` | P0~P1 | 点卯/问安高优先防漏 |
| 周期任务 | `periodic:<task>:<chat>` | P1 | 冷却长无需 P0 |
| 星宫维护 | `star:pacify:<chat>` | P0 | 防止星辰损失假设 |
| 星宫收集 | `star:collect:<chat>` | P0 | 收益类高优先 |
| 星宫牵引 | `star:pull:<chat>:<idx>` | P1 | |
| 药园维护 | `herb:maint:<type>:<chat>` | P0 | 影响成长 |
| 药园采药 | `herb:harvest:<chat>` | P0 | 防止溢出 |
| 药园播种 | `herb:plant:<chat>:<idx>` | P1 | |
| 兑换 | `herb:exchange:<seed>:<chat>` | P1 | 资源准备 |
| 元婴出窍 | `yuanying:chuxiao:<chat>` | P1 | 冷却长 |
| AI 回复 | `ai:reply:<msgid>` | P2 | 让位于核心收益 |

### 15.9 失败/异常回退矩阵
| 场景 | 检测锚点 | 回退策略 |
|------|----------|----------|
| 冷却文本缺失 | 期望含“请在”字样未找到 | 使用默认冷却 + 打印 `[WARN] cooldown_fallback` |
| 解析数字失败 | regex 组全为空 | 默认冷却 + `parse_score=0` |
| 重复成功消息 | 同指令成功消息多次 | 第二次忽略 + 计数 | 
| 维护空执行 | “没有需要【XX】” | 移除后续同类计划 |
| 采药无成熟 | “没有需要【采药】” | 清空 mature 缓存 + 延迟正常扫描 |
| 播种已种上 | “播下” | 标记 growing(ETA未知) -> 下次扫描补齐 |
| 资源不足 | “没有【清灵草种子】” | 排 `.兑换` 并标记 `seed_shortage` |
| 出窍中再出窍 | “正在执行” | 延迟 query 归来倒计时 10~15m 后 |

### 15.10 ParseResult 结构
```python
@dataclass
class ParseResult:
    matched: bool
    type: str                  # e.g. 'daily.signin', 'herb.scan', 'star.collect'
    payload: dict              # 解析细节 (count, idx_list, states...)
    cooldown_s: int | None = None
    next_actions: list[str] | None = None  # 需要立即 enqueue 的后续指令
    dedupe_key: str | None = None
    priority: int | None = None
    parse_score: float = 1.0   # 0~1 可信度，fallback 时 <0.5
    raw_text: str | None = None
```

### 15.11 解析实现建议
- 每类模块集中一组 `parse_*` 函数，暴露统一入口 `parse_incoming(message_text)` 返回第一个命中 `ParseResult`。
- 冷却计算工具：`compute_next_ts(base_seconds, jitter_ratio=0.05, floor=None)`。
- 提供测试夹具：加载示例文本（来自 `tests/fixtures/`）验证解析字段。

### 15.12 测试最小集建议
| 类别 | 用例 |
|------|------|
| Daily | 点卯成功/已点卯；问安成功/已问安；传功 1/3 -> 2/3 -> 3/3 -> 超限提示 |
| Periodic | 闭关成功 + 冷却；裂缝风暴 + 冷却；问道冷却文本；引道成功 |
| Star | 精华已成 + 收集；空闲 -> 牵引；安抚无需要；凝聚中 ETA 解析 |
| Herb | 各 6 状态行 + 一键维护成功/无需要；采药成功/无需要；播种成功/已种上；兑换成功/缺种子 |
| YuanYing | 出窍中倒计时；归来奖励；温养可出窍 |
| Cooldown | 小时/分钟/秒 三种组合；异常极短回退逻辑 |

### 15.13 日志字段标准
| 字段 | 示例 | 说明 |
|------|------|------|
| event | send_command / recv_message / parse_result | 事件类型 |
| command | `.观星台` | 发送指令原文 |
| dedupe | `star:collect:-1001` | 实际使用去重键 |
| latency_ms | 832 | 发送->接收耗时 |
| cooldown_s | 43200 | 解析冷却秒数 |
| next_actions | `[".收集精华"]` | 后续动作列表 |
| parse_score | 0.94 | 可信度 |
| account | `acct_a` | 账号标识 |
| chat | `-100123` | 频道ID |

### 15.14 后续拓展占位
- 支持国际化：将关键锚点抽取为本地化表。
- DSL 化配置：允许在配置中声明简单指令-响应映射而无需改代码。
- 灰度策略：为新解析逻辑提供 `shadow_parse` 并比较差异。

---
(文档完)
