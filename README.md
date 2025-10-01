## Telegram每日自动签到/个人、群组、频道消息监控与自动回复

[English](./README_EN.md)

### 功能

- 每日定时和随机误差时间签到
- 根据配置的文本点击键盘
- 调用AI进行图片识别并点击键盘
- 个人、群组、频道消息监控、转发与自动回复
- 根据配置执行动作流
- **新增：频道自动化机器人** (Channel Automation Bot) - [📖 完整使用指南](./BOT_USAGE_GUIDE.md)
  - 每日例行任务自动化（点卯、传功、问安）
  - 周期任务自动化（启阵、助阵、问道、引道、元婴、裂缝探索）
  - 观星台自动化（观星、牵引、收集、安抚）
  - 小药园自动化（扫描、维护、采药、播种）
  - 小智AI集成（WebSocket连接，支持自动重连）
  - 灵活的指令-响应配置（JSON可扩展）
  - 交互式CLI命令引导
  - 一键初始化配置 `tg-signer bot init`

### 🚀 快速开始（频道自动化机器人）

```bash
# 1. 初始化配置
tg-signer bot init

# 2. 登录账号
tg-signer -a 账号名 login

# 3. 创建机器人配置
tg-signer bot config 我的机器人

# 4. 运行机器人（启用AI聊天互动）
tg-signer -a 账号名 bot run 我的机器人 --ai

# 5. 运行机器人（仅活动问答，不启用AI聊天）
tg-signer -a 账号名 bot run 我的机器人
```

**📚 文档导航**: 
- 🗺️ [DOCS_INDEX.md](./DOCS_INDEX.md) - **文档索引与导航**（推荐先看）
- 📖 [BOT_USAGE_GUIDE.md](./BOT_USAGE_GUIDE.md) - 完整使用指南
- 🏗️ [ARCHITECTURE.md](./ARCHITECTURE.md) - 系统架构设计
- 📊 [PROJECT_ANALYSIS.md](./PROJECT_ANALYSIS.md) - 项目分析报告
- 📋 [INTEGRATION_STATUS.md](./INTEGRATION_STATUS.md) - 集成状态报告
- 💼 [ENTERPRISE_TODO.md](./ENTERPRISE_TODO.md) - 企业级改进建议

### 🏗️ 模块化架构 (v1.1 更新)

本项目已完成模块化重构，采用清晰的分层架构：

**核心功能模块** (独立Python文件):
- 📅 `daily_routine.py` - 每日任务管理 (点卯/传功/问安)
- ⏰ `periodic_tasks.py` - 周期任务管理 (闭关/引道/问道/裂缝/启阵)
- ⭐ `star_observation.py` - 星宫自动化 (安抚→观星→牵引→收集)
- 🌿 `herb_garden.py` - 小药园自动化 (维护→采药→播种)
- 🎯 `activity_manager.py` - 活动识别与响应 (5种活动模式)

**工具模块**:
- ⏱️ `cooldown_parser.py` - 智能冷却时间解析 (支持"12小时30分钟"格式)
- ⚙️ `cooldown_config.py` - 冷却配置常量 (所有任务冷却时间)
- 📝 `logger.py` - 按账号分离的日志系统 (`logs/<account>/`)

**技术文档**:
- 🏗️ [ARCHITECTURE.md](./ARCHITECTURE.md) - 完整架构设计（v1.1）
- 📋 [COOLDOWN_RULES.md](./COOLDOWN_RULES.md) - 冷却规则详细说明
- 🎭 [活动回复词.md](./活动回复词.md) - 活动响应规范

**测试覆盖**:
- ✅ 45个单元测试 (100%通过)
- ✅ 冷却解析器完整测试
- ✅ 真实场景测试用例

**关键特性**:
- ✅ 星宫操作顺序：永远先`.安抚星辰`，再`.观星台`
- ✅ 智能冷却解析：自动提取并回退到默认值
- ✅ 按账号日志分离：`logs/<account>/<account>.log`
- ✅ 活动自动识别：魂魄献祭、天机考验、洞府访客等
- ✅ 消息智能过滤：Thread ID、@mention、Reply ID匹配

  **...**

### 安装

需要Python3.9及以上

```sh
pip install -U tg-signer
```

或者为了提升程序速度：

```sh
pip install "tg-signer[speedup]"
```

#### Docker

未上传直接使用的镜像，可以自行build镜像，见 [docker](./docker) 目录下的Dockerfile和 [README](./docker/README.md) 。

### 使用方法

```
Usage: tg-signer [OPTIONS] COMMAND [ARGS]...

  使用<子命令> --help查看使用说明

子命令别名:
  run_once -> run-once
  send_text -> send-text

Options:
  -l, --log-level [debug|info|warn|error]
                                  日志等级, `debug`, `info`, `warn`, `error`
                                  [default: info]
  --log-file PATH                 日志文件路径, 可以是相对路径  [default: tg-signer.log]
  -p, --proxy TEXT                代理地址, 例如: socks5://127.0.0.1:1080,
                                  会覆盖环境变量`TG_PROXY`的值  [env var: TG_PROXY]
  --session_dir PATH              存储TG Sessions的目录, 可以是相对路径  [default: .]
  -a, --account TEXT              自定义账号名称，对应session文件名为<account>.session  [env
                                  var: TG_ACCOUNT; default: my_account]
  -w, --workdir PATH              tg-signer工作目录，用于存储配置和签到记录等  [default:
                                  .signer]
  --session-string TEXT           Telegram Session String,
                                  会覆盖环境变量`TG_SESSION_STRING`的值  [env var:
                                  TG_SESSION_STRING]
  --in-memory                     是否将session存储在内存中，默认为False，存储在文件
  --help                          Show this message and exit.

Commands:
  export                  导出配置，默认为输出到终端。
  import                  导入配置，默认为从终端读取。
  list                    列出已有配置
  list-members            查询聊天（群或频道）的成员, 频道需要管理员权限
  list-schedule-messages  显示已配置的定时消息
  login                   登录账号（用于获取session）
  logout                  登出账号并删除session文件
  monitor                 配置和运行监控
  multi-run               使用一套配置同时运行多个账号
  reconfig                重新配置
  run                     根据任务配置运行签到
  run-once                运行一次签到任务，即使该签到任务今日已执行过
  schedule-messages       批量配置Telegram自带的定时发送消息功能
  send-text               发送一次消息, 请确保当前会话已经"见过"该`chat_id`
  version                 Show version
```

例如:

```sh
tg-signer run
tg-signer run my_sign  # 不询问，直接运行'my_sign'任务
tg-signer run-once my_sign  # 直接运行一次'my_sign'任务
tg-signer send-text 8671234001 /test  # 向chat_id为'8671234001'的聊天发送'/test'文本
tg-signer send-text -- -10006758812 浇水  # 对于负数需要使用POSIX风格，在短横线'-'前方加上'--'
tg-signer send-text --delete-after 1 8671234001 /test  # 向chat_id为'8671234001'的聊天发送'/test'文本, 并在1秒后删除发送的消息
tg-signer list-members --chat_id -1001680975844 --admin  # 列出频道的管理员
tg-signer schedule-messages --crontab '0 0 * * *' --next-times 10 -- -1001680975844 你好  # 在未来10天的每天0点向'-1001680975844'发送消息
tg-signer monitor run  # 配置个人、群组、频道消息监控与自动回复
tg-signer multi-run -a account_a -a account_b same_task  # 使用'same_task'的配置同时运行'account_a'和'account_b'两个账号
```

### 配置代理（如有需要）

`tg-signer`不读取系统代理，可以使用环境变量 `TG_PROXY`或命令参数`--proxy`进行配置

例如：

```sh
export TG_PROXY=socks5://127.0.0.1:7890
```

### 登录

```sh
tg-signer login
```

根据提示输入手机号码和验证码进行登录并获取最近的聊天列表，确保你想要签到的聊天在列表内。

### 发送一次消息

```sh
tg-signer send-text 8671234001 hello  # 向chat_id为'8671234001'的聊天发送'hello'文本
```

### 运行签到任务

```sh
tg-signer run
```

或预先执行任务名：

```sh
tg-signer run linuxdo
```

根据提示进行配置即可。

#### 示例：

```
开始配置任务<linuxdo>
第1个签到
一. Chat ID（登录时最近对话输出中的ID）: 7661096533
二. Chat名称（可选）: jerry bot
三. 开始配置<动作>，请按照实际签到顺序配置。
  1: 发送普通文本
  2: 发送Dice类型的emoji
  3: 根据文本点击键盘
  4: 根据图片选择选项
  5: 回复计算题

第1个动作:
1. 输入对应的数字选择动作: 1
2. 输入要发送的文本: checkin
3. 是否继续添加动作？(y/N)：y
第2个动作:
1. 输入对应的数字选择动作: 3
2. 键盘中需要点击的按钮文本: 签到
3. 是否继续添加动作？(y/N)：y
第3个动作:
1. 输入对应的数字选择动作: 4
图片识别将使用大模型回答，请确保大模型支持图片识别。
2. 是否继续添加动作？(y/N)：y
第4个动作:
1. 输入对应的数字选择动作: 5
计算题将使用大模型回答。
2. 是否继续添加动作？(y/N)：y
第5个动作:
1. 输入对应的数字选择动作: 2
2. 输入要发送的骰子（如 🎲, 🎯）: 🎲
3. 是否继续添加动作？(y/N)：n
在运行前请通过环境变量正确设置`OPENAI_API_KEY`, `OPENAI_BASE_URL`。默认模型为"gpt-4o", 可通过环境变量`OPENAI_MODEL`更改。
四. 等待N秒后删除签到消息（发送消息后等待进行删除, '0'表示立即删除, 不需要删除直接回车）, N: 10
╔════════════════════════════════════════════════╗
║ Chat ID: 7661096533                            ║
║ Name: jerry bot                                ║
║ Delete After: 10                               ║
╟────────────────────────────────────────────────╢
║ Actions Flow:                                  ║
║ 1. [发送普通文本] Text: checkin                ║
║ 2. [根据文本点击键盘] Click: 签到              ║
║ 3. [根据图片选择选项]                          ║
║ 4. [回复计算题]                                ║
║ 5. [发送Dice类型的emoji] Dice: 🎲              ║
╚════════════════════════════════════════════════╝
第1个签到配置成功

继续配置签到？(y/N)：n
每日签到时间（time或crontab表达式，如'06:00:00'或'0 6 * * *'）:
签到时间误差随机秒数（默认为0）: 300
```

### 配置与运行监控

```sh
tg-signer monitor run my_monitor
```

根据提示进行配置。

#### 示例：

```
开始配置任务<my_monitor>
聊天chat id和用户user id均同时支持整数id和字符串username, username必须以@开头，如@neo

配置第1个监控项
1. Chat ID（登录时最近对话输出中的ID）: -4573702599
2. 匹配规则('exact', 'contains', 'regex', 'all'): contains
3. 规则值（不可为空）: kfc
4. 只匹配来自特定用户ID的消息（多个用逗号隔开, 匹配所有用户直接回车）: @neo
5. 默认发送文本: V Me 50
6. 从消息中提取发送文本的正则表达式:
7. 等待N秒后删除签到消息（发送消息后等待进行删除, '0'表示立即删除, 不需要删除直接回车）, N:
继续配置？(y/N)：y

配置第2个监控项
1. Chat ID（登录时最近对话输出中的ID）: -4573702599
2. 匹配规则('exact', 'contains', 'regex'): regex
3. 规则值（不可为空）: 参与关键词：「.*?」
4. 只匹配来自特定用户ID的消息（多个用逗号隔开, 匹配所有用户直接回车）: 61244351
5. 默认发送文本:
6. 从消息中提取发送文本的正则表达式: 参与关键词：「(?P<keyword>(.*?))」\n
7. 等待N秒后删除签到消息（发送消息后等待进行删除, '0'表示立即删除, 不需要删除直接回车）, N: 5
继续配置？(y/N)：y

配置第3个监控项
1. Chat ID（登录时最近对话输出中的ID）: -4573702599
2. 匹配规则(exact, contains, regex, all): all
3. 只匹配来自特定用户ID的消息（多个用逗号隔开, 匹配所有用户直接回车）:
4. 总是忽略自己发送的消息（y/N）: y
5. 默认发送文本（不需要则回车）:
6. 是否使用AI进行回复(y/N): n
7. 从消息中提取发送文本的正则表达式（不需要则直接回车）:
8. 是否通过Server酱推送消息(y/N): n
9. 是否需要转发到外部（UDP, Http）(y/N): y
10. 是否需要转发到UDP(y/N): y
11. 请输入UDP服务器地址和端口（形如`127.0.0.1:1234`）: 127.0.0.1:9999
12. 是否需要转发到Http(y/N): y
13. 请输入Http地址（形如`http://127.0.0.1:1234`）: http://127.0.0.1:8000/tg/user1/messages
继续配置？(y/N)：n

```

#### 示例解释：

1. 聊天`chat id`和用户`user id`均同时支持整数**id**和字符串**username**, username**必须以@开头** 如"neo"输入"@neo"，注意*
   *username** 可能不存在，示例中`chat id`为-4573702599表示规则只对-4573702599对应的聊天有效。

2. 匹配规则，目前皆**忽略大小写**：

    1. `exact` 为精确匹配，消息必须精确等于该值。

    2. `contains` 为包含匹配，如contains="kfc"，那么只要收到的消息中包含"kfc"如"I like MacDonalds rather than KfC"
       即匹配到（注意忽略了大小写）

    3. `regex` 为正则，参考  [Python正则表达式](https://docs.python.org/zh-cn/3/library/re.html) ，在消息中有**搜索到该正则即匹配
       **，示例中的 "参与关键词：「.*?」" 可以匹配消息： "新的抽奖已经创建...
       参与关键词：「我要抽奖」

       建议先私聊机器人"

    4. 可以只匹配来自特定用户的消息，如群管理员而不是随便什么人发布的抽奖消息

    5. 可以设置默认发布文本， 即只要匹配到消息即默认发送该文本

    6. 提取发布文本的正则，例如 "参与关键词：「(.*?)」\n" ，注意用括号`(...)` 捕获要提取的文本，
       可以捕获第3点示例消息的关键词"我要抽奖"并自动发送

3. 消息Message结构参考:

```json
{
    "_": "Message",
    "id": 2950,
    "from_user": {
        "_": "User",
        "id": 123456789,
        "is_self": false,
        "is_contact": false,
        "is_mutual_contact": false,
        "is_deleted": false,
        "is_bot": false,
        "is_verified": false,
        "is_restricted": false,
        "is_scam": false,
        "is_fake": false,
        "is_support": false,
        "is_premium": false,
        "is_contact_require_premium": false,
        "is_close_friend": false,
        "is_stories_hidden": false,
        "is_stories_unavailable": true,
        "is_business_bot": false,
        "first_name": "linux",
        "status": "UserStatus.ONLINE",
        "next_offline_date": "2025-05-30 11:52:40",
        "username": "linuxdo",
        "dc_id": 5,
        "phone_number": "*********",
        "photo": {
            "_": "ChatPhoto",
            "small_file_id": "AQADBQADqqcxG6hqrTMAEAIAA6hqrTMABLkwVDcqzBjAAAQeBA",
            "small_photo_unique_id": "AgADqqcxG6hqrTM",
            "big_file_id": "AQADBQADqqcxG6hqrTMAEAMAA6hqrTMABLkwVDcqzBjAAAQeBA",
            "big_photo_unique_id": "AgADqqcxG6hqrTM",
            "has_animation": false,
            "is_personal": false
        },
        "added_to_attachment_menu": false,
        "inline_need_location": false,
        "can_be_edited": false,
        "can_be_added_to_attachment_menu": false,
        "can_join_groups": false,
        "can_read_all_group_messages": false,
        "has_main_web_app": false
    },
    "date": "2025-05-30 11:47:46",
    "chat": {
        "_": "Chat",
        "id": -52737131599,
        "type": "ChatType.GROUP",
        "is_creator": true,
        "is_deactivated": false,
        "is_call_active": false,
        "is_call_not_empty": false,
        "title": "测试组",
        "has_protected_content": false,
        "members_count": 4,
        "permissions": {
            "_": "ChatPermissions",
            "can_send_messages": true,
            "can_send_media_messages": true,
            "can_send_other_messages": true,
            "can_send_polls": true,
            "can_add_web_page_previews": true,
            "can_change_info": true,
            "can_invite_users": true,
            "can_pin_messages": true,
            "can_manage_topics": true
        }
    },
    "from_offline": false,
    "show_caption_above_media": false,
    "mentioned": false,
    "scheduled": false,
    "from_scheduled": false,
    "edit_hidden": false,
    "has_protected_content": false,
    "text": "test, 测试",
    "video_processing_pending": false,
    "outgoing": false
}
```

#### 示例运行输出：

```
[INFO] [tg-signer] 2024-10-25 12:29:06,516 core.py 458 开始监控...
[INFO] [tg-signer] 2024-10-25 12:29:37,034 core.py 439 匹配到监控项：MatchConfig(chat_id=-4573702599, rule=contains, rule_value=kfc), default_send_text=V me 50, send_text_search_regex=None
[INFO] [tg-signer] 2024-10-25 12:29:37,035 core.py 442 发送文本：V me 50
[INFO] [tg-signer] 2024-10-25 12:30:02,726 core.py 439 匹配到监控项：MatchConfig(chat_id=-4573702599, rule=regex, rule_value=参与关键词：「.*?」), default_send_text=None, send_text_search_regex=参与关键词：「(?P<keyword>(.*?))」\n
[INFO] [tg-signer] 2024-10-25 12:30:02,727 core.py 442 发送文本：我要抽奖
[INFO] [tg-signer] 2024-10-25 12:30:03,001 core.py 226 Message「我要抽奖」 to -4573702599 will be deleted after 5 seconds.
[INFO] [tg-signer] 2024-10-25 12:30:03,001 core.py 229 Waiting...
[INFO] [tg-signer] 2024-10-25 12:30:08,260 core.py 232 Message「我要抽奖」 to -4573702599 deleted!
```



### 版本变动日志

#### 0.8.0
- 支持单个账号同一进程内同时运行多个任务

#### 0.7.6
- fix: 监控多个聊天时消息转发至每个聊天 (#55)

#### 0.7.5
- 捕获并记录执行任务期间的所有RPC错误
- bump kurigram version to 2.2.7

#### 0.7.4
- 执行多个action时，支持固定时间间隔
- 通过`crontab`配置定时执行时不再限制每日执行一次

#### 0.7.2
- 支持将消息转发至外部端点，通过：
  - UDP
  - HTTP
- 将kurirogram替换为kurigram

#### 0.7.0
- 支持每个聊天会话按序执行多个动作，动作类型：
  - 发送文本
  - 发送骰子
  - 按文本点击键盘
  - 通过图片选择选项
  - 通过计算题回复

#### 0.6.6
- 增加对发送DICE消息的支持

#### 0.6.5
- 修复使用同一套配置运行多个账号时签到记录共用的问题

#### 0.6.4
- 增加对简单计算题的支持
- 改进签到配置和消息处理

#### 0.6.3
- 兼容kurigram 2.1.38版本的破坏性变更
> Remove coroutine param from run method [a7afa32](https://github.com/KurimuzonAkuma/pyrogram/commit/a7afa32df208333eecdf298b2696a2da507bde95)


#### 0.6.2
- 忽略签到时发送消息失败的聊天

#### 0.6.1
- 支持点击按钮文本后继续进行图片识别

#### 0.6.0
- Signer支持通过crontab定时
- Monitor匹配规则添加`all`支持所有消息
- Monitor支持匹配到消息后通过server酱推送
- Signer新增`multi-run`用于使用一套配置同时运行多个账号

#### 0.5.2
- Monitor支持配置AI进行消息回复
- 增加批量配置「Telegram自带的定时发送消息功能」的功能

#### 0.5.1
- 添加`import`和`export`命令用于导入导出配置

#### 0.5.0
- 根据配置的文本点击键盘
- 调用AI识别图片点击键盘



### 配置与数据存储位置

数据和配置默认保存在 `.signer` 目录中。然后运行 `tree .signer`，你将看到：

```
.signer
├── latest_chats.json  # 获取的最近对话
├── me.json  # 个人信息
├── monitors  # 监控
│   ├── my_monitor  # 监控任务名
│       └── config.json  # 监控配置
├── signs  # 签到任务
│   └── linuxdo  # 签到任务名
│       ├── config.json  # 签到配置
│       └── sign_record.json  # 签到记录
└── bot_configs  # 机器人配置 (新增)
    └── my_bot  # 机器人任务名
        └── config.json  # 机器人配置

3 directories, 4 files
```

### 频道自动化机器人使用说明

频道自动化机器人是一个功能强大的自动化工具，基于 [ARCHITECTURE.md](./ARCHITECTURE.md) 设计，支持多种自动化任务。

#### 快速开始

1. **登录账号**（如果还没有登录）

```bash
tg-signer login
```

2. **配置机器人**（交互式配置）

```bash
tg-signer bot config my_bot
```

这将启动交互式配置向导，引导你完成：
- 频道ID配置
- 每日任务配置（点卯、传功、问安）
- 周期任务配置（启阵、助阵、问道、引道、元婴、裂缝探索）
- 观星台配置
- 小药园配置
- 小智AI配置

3. **配置小智AI**（可选）

创建 `config.json` 文件（已提供示例）：

```json
{
  "SYSTEM_OPTIONS": {
    "NETWORK": {
      "WEBSOCKET_URL": "wss://api.tenclass.net/xiaozhi/v1/",
      "WEBSOCKET_ACCESS_TOKEN": "test-token"
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

4. **运行机器人**

```bash
tg-signer bot run my_bot
```

如果需要指定小智AI配置文件：

```bash
tg-signer bot run my_bot --xiaozhi-config /path/to/config.json
```

#### 机器人管理命令

```bash
# 列出所有机器人配置
tg-signer bot list

# 导出机器人配置
tg-signer bot export my_bot -o my_bot_config.json

# 导入机器人配置
tg-signer bot import my_bot -i my_bot_config.json

# 检查机器人环境和配置
tg-signer bot doctor
tg-signer bot doctor my_bot
```

#### 配置文件结构

机器人配置文件示例（参考 `example_bot_config.json`）：

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
  "xiaozhi_ai": {
    "authorized_users": [123456789],
    "filter_keywords": ["广告", "刷屏"],
    "blacklist_users": [],
    "trigger_keywords": ["@小智", "小智AI", "xiaozhi"],
    "response_prefix": "小智AI回复: "
  },
  "custom_rules": [
    {
      "pattern": "测试.*",
      "response": "这是自动回复",
      "cooldown_seconds": 300,
      "priority": 5,
      "enabled": true
    }
  ]
}
```

#### 灵活的指令-响应配置

通过 `custom_rules` 字段，你可以灵活配置指令-响应规则，无需修改代码：

```json
{
  "custom_rules": [
    {
      "pattern": "问候.*",
      "response": "你好！",
      "cooldown_seconds": 60,
      "priority": 5,
      "enabled": true
    },
    {
      "pattern": "帮助",
      "response": "这是帮助信息...",
      "cooldown_seconds": 300,
      "priority": 3,
      "enabled": true
    }
  ]
}
```

#### 功能特性

- ✅ **账号登录缓存管理**：沿用 tg-signer 体系，无需改动
- ✅ **小智AI集成**：简单移植自 [py-xiaozhi](https://github.com/AlexYao521/py-xiaozhi)
- ✅ **配置兼容**：直接使用 `config.json` 和 `efuse.json`
- ✅ **功能开关**：所有功能可通过配置开关控制
- ✅ **灵活扩展**：指令-响应可通过JSON灵活配置
- ✅ **交互式CLI**：命令行交互引导，简单易用
- ✅ **状态持久化**：自动保存任务状态，支持断点续传
- ✅ **优先级队列**：智能调度，重要任务优先执行
- ✅ **去重机制**：防止重复执行相同任务

#### 架构设计

详细架构设计请参考 [ARCHITECTURE.md](./ARCHITECTURE.md)，包含：
- 模块划分与职责
- 配置体系设计
- 状态文件与数据结构
- 并发调度模型
- 指令与响应规范

#### 注意事项

1. 确保设置了环境变量 `TG_API_ID` 和 `TG_API_HASH`
2. 小智AI的 `WEBSOCKET_ACCESS_TOKEN` 配置已验证可用，可直接使用
3. 首次使用需要先登录账号：`tg-signer login`
4. 建议先使用 `doctor` 命令检查环境
5. 配置文件中的频道ID为负数，记得在命令行中使用 `--` 分隔符

#### 故障排查

如果遇到问题，可以：

1. 检查环境和配置：
```bash
tg-signer bot doctor my_bot
```

2. 查看日志文件：
```bash
tail -f tg-signer.log
```

3. 使用调试模式：
```bash
tg-signer --log-level debug bot run my_bot
```
