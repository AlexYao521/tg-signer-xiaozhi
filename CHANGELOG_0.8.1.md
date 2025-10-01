# Changelog for Version 0.8.1

## 发布日期 / Release Date
2025-01-02

## 版本信息 / Version Information
- 版本号 / Version: 0.8.1
- 上一版本 / Previous Version: 0.8.0

## 修复的问题 / Fixed Issues

### Issue #6: 修复 herb_garden.py 中的 AttributeError 错误
**问题描述：**
运行机器人时出现 `AttributeError: 'HerbGarden' object has no attribute 'parse_garden_status'` 错误，导致小药园功能无法正常工作。

**错误日志：**
```
ERROR    | tg-signer.bot | bot_worker.py:336 | Error handling message: 'HerbGarden' object has no attribute 'parse_garden_status'
```

**修复内容：**
1. 将 `herb_garden.py` 中的 `parse_garden_status` 方法调用改为 `parse_scan_response`
2. 修复了 `get_maintenance_and_harvest_commands` 方法不存在的问题，直接使用 `parse_scan_response` 返回的命令列表
3. 代码现在正确解析小药园状态并生成维护命令

**影响范围：**
- 文件：`tg_signer/herb_garden.py`
- 影响：启用小药园功能的所有机器人

---

### Issue #4: 版本号更新
**问题描述：**
用户希望每次更改分支后，版本号能够变化，以便识别使用的是新版本。

**修复内容：**
- 版本号从 `0.8.0` 更新到 `0.8.1`
- 可以通过 `tg-signer version` 命令查看当前版本

**影响范围：**
- 文件：`tg_signer/__init__.py`

---

### Issue #1: 完善 example.json 配置
**问题描述：**
`example.json` 配置不完整，缺少很多模块的配置选项，用户不清楚有哪些可用配置。

**修复内容：**
1. **更新 `bot init` 命令**
   - 创建的 `example.json` 包含所有模块的完整配置
   - 添加了小药园（herb_garden）的详细配置，包括种子配置、扫描间隔等
   - 添加了小智AI的触发关键词、响应前缀等配置
   - 添加了自定义规则和时间间隔配置

2. **更新 `bot config` 命令**
   - 交互式配置时询问小药园的默认种子
   - 生成的配置包含所有必要字段

3. **更新 `example_bot_config.json`**
   - 添加了详细的注释说明每个配置项的用途
   - 所有功能模块的配置都包含在内
   - 默认禁用高级功能（观星台、小药园），避免新手误用

**影响范围：**
- 文件：`tg_signer/cli/bot.py`, `example_bot_config.json`
- 影响：所有使用 `tg-signer bot init` 和 `tg-signer bot config` 的用户

---

### Issue #3: 添加按账号记录日志功能
**问题描述：**
用户希望能够按账号分别记录日志，方便分析各个账号的运行情况。

**修复内容：**
1. **Logger 增强**
   - `logger.py` 已经支持按账号记录日志
   - 日志文件保存在 `logs/<账号名>/<账号名>.log`
   - 每个账号的日志独立存储

2. **CLI 更新**
   - 更新 `signer.py` 中的 `configure_logger` 调用，传入账号参数
   - 当运行 `login`, `run`, `run-once` 等命令时自动启用账号日志

3. **文档更新**
   - 在 `BOT_USAGE_GUIDE.md` 中添加了查看账号日志的说明
   - 提供了使用 `tail -f` 和 `grep` 查看日志的示例

**使用方法：**
```bash
# 运行机器人（自动记录到 logs/my_account/my_account.log）
tg-signer -a my_account bot run my_channel

# 查看账号日志
tail -f logs/my_account/my_account.log

# 搜索错误日志
grep "ERROR" logs/my_account/my_account.log
```

**影响范围：**
- 文件：`tg_signer/cli/signer.py`, `BOT_USAGE_GUIDE.md`, `.gitignore`
- 影响：所有使用命令行运行机器人的用户

---

### Issue #5: 添加开发模式支持
**问题描述：**
使用 `pip install -e .` 后，每次修改代码都需要重新安装才能生效，影响开发效率。

**修复内容：**
1. **创建 DEVELOPMENT_GUIDE.md**
   - 详细说明了 5 种开发模式方法
   - 包括使用 PYTHONPATH、直接运行模块、开发脚本等
   - 提供了调试技巧和常见问题解答
   - 说明了版本管理和发布流程

2. **创建开发脚本**
   - `run_dev.py`: Python 开发脚本，无需安装即可运行
   - `dev.sh`: Linux/Mac 开发便捷脚本
   - `dev.ps1`: Windows PowerShell 开发便捷脚本

3. **使用方法**
   ```bash
   # 方法一：直接运行 Python 脚本
   python run_dev.py -a 账号名 bot run 配置名
   
   # 方法二：使用 shell 脚本（Linux/Mac）
   ./dev.sh -a 账号名 bot run 配置名
   
   # 方法三：使用 PowerShell 脚本（Windows）
   .\dev.ps1 -a 账号名 bot run 配置名
   ```

**影响范围：**
- 新增文件：`DEVELOPMENT_GUIDE.md`, `run_dev.py`, `dev.sh`, `dev.ps1`
- 影响：所有开发者和贡献者

---

## 文档更新 / Documentation Updates

### BOT_USAGE_GUIDE.md
1. **新增 FAQ**
   - 如何处理 SLOWMODE_WAIT_X 错误
   - 如何查看每个账号的日志

2. **SLOWMODE 错误说明**
   - 解释了 Telegram 慢速模式的工作原理
   - 提供了调整配置的方法
   - 说明这是正常行为，不是 bug

### 新增 DEVELOPMENT_GUIDE.md
- 5 种开发模式的详细说明
- 调试技巧
- 版本管理规范
- 最佳实践
- 常见问题解答

---

## 技术细节 / Technical Details

### 修改的文件列表
```
M  .gitignore
M  BOT_USAGE_GUIDE.md
A  DEVELOPMENT_GUIDE.md
A  dev.ps1
A  dev.sh
M  example_bot_config.json
A  run_dev.py
M  tg_signer/__init__.py
M  tg_signer/cli/bot.py
M  tg_signer/cli/signer.py
M  tg_signer/herb_garden.py
```

### 代码统计
- 新增文件：5 个
- 修改文件：6 个
- 新增代码行数：约 500 行
- 修复 Bug：2 个关键 bug

---

## 升级建议 / Upgrade Recommendations

### 对于现有用户
1. **更新代码**
   ```bash
   git pull origin main
   pip install -e . --upgrade
   ```

2. **验证版本**
   ```bash
   tg-signer version
   # 应该显示: tg-signer 0.8.1
   ```

3. **检查配置**
   - 如果使用小药园功能，此更新修复了关键 bug，建议立即更新
   - 如果遇到 SLOWMODE 错误，请参考更新后的文档调整配置

4. **查看日志**
   - 检查新的日志目录：`logs/<账号名>/`
   - 清理旧的日志文件（可选）

### 对于开发者
1. **使用开发脚本**
   ```bash
   # 复制开发脚本
   chmod +x dev.sh run_dev.py
   
   # 使用开发模式运行
   ./dev.sh -a test_account version
   ```

2. **阅读开发指南**
   ```bash
   # 查看 DEVELOPMENT_GUIDE.md 了解详细开发流程
   cat DEVELOPMENT_GUIDE.md
   ```

---

## 已知问题 / Known Issues

1. **测试失败**
   - `test_yuanying_tasks.py` 存在导入错误
   - 这是预先存在的问题，不是本次更新引入的
   - 不影响实际运行

2. **依赖缺失警告**
   - 可能看到 "TgCrypto is missing" 警告
   - 这是性能优化的可选依赖，不影响功能
   - 如需安装：`pip install TgCrypto`

---

## 下一步计划 / Next Steps

根据用户反馈，后续版本可能包含：
1. 更智能的慢速模式处理
2. 更多的自定义规则支持
3. Web UI 管理界面
4. 更完善的测试覆盖

---

## 贡献者 / Contributors

感谢以下贡献者：
- @AlexYao521 - 项目维护者
- GitHub Copilot - 代码审查和修复

---

## 反馈 / Feedback

如有问题或建议，请：
1. 提交 Issue 到 GitHub 仓库
2. 查看 `BOT_USAGE_GUIDE.md` 和 `DEVELOPMENT_GUIDE.md`
3. 加入社区讨论
