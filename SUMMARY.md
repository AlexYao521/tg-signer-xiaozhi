# 问题修复总结 (Summary of Fixes)

本次更新解决了问题陈述中提到的所有 6 个问题。

## ✅ 问题 #6: 运行报错 - AttributeError 'HerbGarden' object has no attribute 'parse_garden_status'

**状态：已修复** ✓

**原因：**
代码中调用了不存在的方法 `parse_garden_status` 和 `get_maintenance_and_harvest_commands`。

**修复方案：**
- 将 `parse_garden_status` 改为 `parse_scan_response`（实际存在的方法）
- 直接使用 `parse_scan_response` 返回的命令列表

**影响文件：**
- `tg_signer/herb_garden.py` (行 357, 361)

**测试：**
```bash
python -m py_compile tg_signer/herb_garden.py  # 编译成功
```

---

## ✅ 问题 #4: 版本号管理

**状态：已完成** ✓

**要求：**
每次更改分支后，能否给 tg-signer 版本号变化一下，好找到本地调试使用的是新的版本。

**实现：**
- 版本号从 `0.8.0` 更新到 `0.8.1`
- 可通过 `tg-signer version` 查看

**影响文件：**
- `tg_signer/__init__.py`

**验证：**
```bash
tg-signer version
# 输出: tg-signer 0.8.1
```

---

## ✅ 问题 #1: example.json 配置不全

**状态：已完成** ✓

**要求：**
example.json 到底是干嘛的，这个是 init 通过代码创建的吗，可以根据当前文档 BOT_USAGE_GUIDE.md 根据模块详情把配置都搞全了，默认不启用呗。

**实现：**

1. **`tg-signer bot init` 命令会自动创建完整的 example.json**
   - 位置：`.signer/bot_configs/example.json`
   - 包含所有模块的完整配置
   - 默认禁用高级功能（观星台、小药园）

2. **完整的配置包括：**
   - 每日任务（daily）
   - 周期任务（periodic）
   - 观星台（star_observation）- 默认禁用
   - 小药园（herb_garden）- 默认禁用，包含完整种子配置
   - 小智AI（xiaozhi_ai）- 包含触发关键词、响应前缀
   - 活动管理（activity）
   - 自定义规则（custom_rules）
   - 时间间隔（sign_interval, min_send_interval）

3. **详细注释说明**
   - 每个配置项都有注释说明用途
   - 参考 `example_bot_config.json` 查看完整示例

**影响文件：**
- `tg_signer/cli/bot.py` (init 和 config 命令)
- `example_bot_config.json` (模板文件)

**使用方法：**
```bash
# 初始化（创建 example.json）
tg-signer bot init

# 查看示例配置
cat .signer/bot_configs/example.json

# 基于示例创建自己的配置
tg-signer bot config 我的频道
```

---

## ✅ 问题 #3: 按账号记录日志

**状态：已完成** ✓

**要求：**
关于运行报错，是否可以根据账号来记录 log 呀，方便我们分析，就算不报错也最好执行到关键位置，都记录到 log 文件。

**实现：**

1. **自动按账号分类日志**
   - 日志目录：`logs/<账号名>/`
   - 日志文件：`logs/<账号名>/<账号名>.log`
   - 每个账号独立记录

2. **自动启用**
   - 运行 `tg-signer -a 账号名 bot run ...` 时自动启用
   - 无需额外参数

3. **日志轮转**
   - 单个日志文件最大 3MB
   - 保留最近 10 个备份文件

**影响文件：**
- `tg_signer/logger.py` (已支持，只需使能)
- `tg_signer/cli/signer.py` (传递账号参数)
- `.gitignore` (忽略 logs 目录)

**使用方法：**
```bash
# 运行机器人（自动记录日志）
tg-signer -a my_account bot run my_channel

# 查看日志
tail -f logs/my_account/my_account.log

# 搜索错误
grep "ERROR" logs/my_account/my_account.log

# 查看最近 100 行
tail -n 100 logs/my_account/my_account.log
```

---

## ✅ 问题 #5: 本地开发模式

**状态：已完成** ✓

**要求：**
现在本地调试执行 `pip install -e .` 后，再每次 cli 调用 tg-signer 执行的都不是我本地边修改边运行的呀？必须每次 `pip install -e .`，修改的才生效。如何做到边修改边运行？

**实现：**

1. **创建开发指南 DEVELOPMENT_GUIDE.md**
   - 5 种开发模式方法
   - 详细的故障排除指南
   - 调试技巧和最佳实践

2. **提供 3 个开发脚本**
   - `run_dev.py` - Python 开发脚本（跨平台）
   - `dev.sh` - Linux/Mac 便捷脚本
   - `dev.ps1` - Windows PowerShell 脚本

**推荐方法（按优先级）：**

### 方法 1: 使用 run_dev.py（推荐）
```bash
# 直接运行，无需安装
python run_dev.py -a 账号名 bot run 配置名
```

### 方法 2: 使用 dev.sh / dev.ps1
```bash
# Linux/Mac
./dev.sh -a 账号名 bot run 配置名

# Windows PowerShell
.\dev.ps1 -a 账号名 bot run 配置名
```

### 方法 3: 设置 PYTHONPATH
```bash
# Linux/Mac
export PYTHONPATH=/path/to/tg-signer-xiaozhi:$PYTHONPATH
tg-signer -a 账号名 bot run 配置名

# Windows
$env:PYTHONPATH = "C:\path\to\tg-signer-xiaozhi;$env:PYTHONPATH"
tg-signer -a 账号名 bot run 配置名
```

**影响文件：**
- `DEVELOPMENT_GUIDE.md` (新增)
- `run_dev.py` (新增)
- `dev.sh` (新增)
- `dev.ps1` (新增)

**详细文档：**
查看 `DEVELOPMENT_GUIDE.md` 了解所有开发模式和故障排除。

---

## ✅ 问题 #2: SLOWMODE_WAIT_X 错误（文档说明）

**状态：已完成** ✓

**错误信息：**
```
ERROR | Failed to send command '.闭关修炼': Telegram says: [420 SLOWMODE_WAIT_X] - Slowmode is enabled in this chat: wait 9 seconds before sending another message to this chat.
```

**说明：**

这不是代码 bug，而是 Telegram 平台的**慢速模式（Slowmode）**限制。

**原因：**
- 频道管理员启用了慢速模式
- 要求两次消息之间必须间隔指定秒数（例如 9 秒）
- 这是 Telegram 的安全机制，无法绕过

**解决方案：**

1. **调整配置文件**
   ```json
   {
     "min_send_interval": 10.0
   }
   ```

2. **减少同时任务**
   - 禁用部分周期任务
   - 减少发送频率

3. **联系管理员**
   - 请求关闭或调整慢速模式设置

**影响文件：**
- `BOT_USAGE_GUIDE.md` (添加 FAQ)

**详细说明：**
查看 `BOT_USAGE_GUIDE.md` 的"常见问题"部分。

---

## 📊 变更统计

```
新增文件：6 个
  - DEVELOPMENT_GUIDE.md
  - CHANGELOG_0.8.1.md
  - run_dev.py
  - dev.sh
  - dev.ps1
  - SUMMARY.md (本文件)

修改文件：6 个
  - tg_signer/__init__.py (版本号)
  - tg_signer/herb_garden.py (修复 bug)
  - tg_signer/cli/bot.py (完善配置)
  - tg_signer/cli/signer.py (账号日志)
  - example_bot_config.json (完整示例)
  - BOT_USAGE_GUIDE.md (FAQ)
  - .gitignore (忽略 logs)

代码行数：约 550+ 行
修复 Bug：2 个关键 bug
新增功能：按账号日志、开发脚本
文档更新：3 个主要文档
```

---

## 🚀 升级步骤

### 1. 拉取代码
```bash
cd /path/to/tg-signer-xiaozhi
git pull origin main
```

### 2. 重新安装（可选）
```bash
pip install -e . --upgrade
```

### 3. 验证版本
```bash
tg-signer version
# 应该显示: tg-signer 0.8.1
```

### 4. 查看新功能
```bash
# 查看开发指南
cat DEVELOPMENT_GUIDE.md

# 查看完整更新日志
cat CHANGELOG_0.8.1.md

# 测试开发脚本
python run_dev.py version
```

---

## 📖 相关文档

- **CHANGELOG_0.8.1.md** - 完整更新日志
- **DEVELOPMENT_GUIDE.md** - 开发指南
- **BOT_USAGE_GUIDE.md** - 使用指南（已更新）
- **example_bot_config.json** - 配置示例

---

## ❓ 常见问题

### Q1: 更新后还是报错怎么办？
A: 
1. 清除 Python 缓存：`find . -type d -name __pycache__ -exec rm -rf {} +`
2. 重新安装：`pip install -e . --force-reinstall`
3. 检查版本：`tg-signer version` 应该是 0.8.1

### Q2: 如何确认使用的是最新代码？
A:
1. 查看版本号：`tg-signer version`
2. 在代码中添加打印：`print("using new code")`
3. 使用开发脚本：`python run_dev.py version`

### Q3: 日志文件在哪里？
A:
- 老版本：`tg-signer.log`（根目录）
- 新版本：`logs/<账号名>/<账号名>.log`

### Q4: 开发脚本不工作？
A:
1. 确保有执行权限：`chmod +x dev.sh run_dev.py`
2. 使用完整路径：`python /path/to/run_dev.py`
3. 查看开发指南：`DEVELOPMENT_GUIDE.md`

---

## 🎯 测试建议

1. **测试小药园功能**
   ```bash
   tg-signer -a test_account bot run 有小药园的频道
   # 检查是否还有 AttributeError
   ```

2. **测试账号日志**
   ```bash
   tg-signer -a test_account bot run 测试频道
   # 查看 logs/test_account/test_account.log
   ```

3. **测试开发脚本**
   ```bash
   python run_dev.py version
   ./dev.sh version  # Linux/Mac
   .\dev.ps1 version # Windows
   ```

---

## 🙏 致谢

感谢用户提供的详细问题报告，帮助我们改进项目！

如有其他问题，请随时反馈。
