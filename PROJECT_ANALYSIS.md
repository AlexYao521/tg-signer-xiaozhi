# 项目架构与功能完整分析报告

> 生成日期: 2024
> 
> 本文档对整个 tg-signer-xiaozhi 项目进行全面分析，包括架构设计、功能完善度、文档组织和企业级改进建议。

---

## 目录

1. [项目概述](#1-项目概述)
2. [项目架构分析](#2-项目架构分析)
3. [功能完善情况](#3-功能完善情况)
4. [文档组织现状](#4-文档组织现状)
5. [企业级建议与TODO](#5-企业级建议与todo)
6. [维护指南](#6-维护指南)

---

## 1. 项目概述

### 1.1 项目定位

**tg-signer-xiaozhi** 是一个功能完善的 Telegram 自动化工具，主要用于：
- Telegram 频道自动签到和互动
- 个人、群组、频道消息监控与自动回复
- 修仙游戏频道自动化（每日任务、周期任务、观星台、小药园等）
- AI 对话集成（小智AI）

### 1.2 技术栈

- **语言**: Python 3.9+
- **核心库**: Pyrogram (kurigram 2.2.7)
- **配置管理**: Pydantic
- **异步框架**: asyncio
- **测试框架**: pytest
- **日志**: Python logging + RotatingFileHandler
- **状态存储**: JSON 文件（原子写入）

### 1.3 代码规模

```
核心代码模块: 24个Python文件
测试文件: 10个测试套件
文档文件: 16个Markdown文档
代码行数: ~8000+ 行（估算）
测试覆盖: 45+ 测试用例
```

---

## 2. 项目架构分析

### 2.1 整体架构

项目采用**模块化分层架构**，核心组件包括：

```
┌─────────────────────────────────────────┐
│          CLI Layer (cli/)               │
│  ├─ bot.py (机器人命令)                 │
│  ├─ signer.py (签到命令)                │
│  └─ monitor.py (监控命令)               │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Core Worker Layer (core.py)        │
│  ├─ BaseUserWorker (基础工作器)         │
│  ├─ UserSigner (签到工作器)             │
│  ├─ UserMonitor (监控工作器)            │
│  └─ BotWorker (机器人工作器)            │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│     Business Logic Layer (modules/)     │
│  ├─ daily_routine.py (每日任务)         │
│  ├─ periodic_tasks.py (周期任务)        │
│  ├─ star_observation.py (观星台)        │
│  ├─ herb_garden.py (小药园)             │
│  ├─ yuanying_tasks.py (元婴任务)        │
│  ├─ activity_manager.py (活动管理)      │
│  └─ xiaozhi_client.py (小智AI)          │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│     Infrastructure Layer (utils/)       │
│  ├─ cooldown_parser.py (冷却解析)       │
│  ├─ cooldown_config.py (冷却配置)       │
│  ├─ logger.py (日志系统)                │
│  ├─ bot_config.py (配置管理)            │
│  └─ utils.py (工具函数)                 │
└─────────────────────────────────────────┘
```

### 2.2 核心模块职责

| 模块 | 文件 | 职责 | 状态 |
|------|------|------|------|
| 每日任务 | `daily_routine.py` | 点卯、传功、问安 | ✅ 完成 |
| 周期任务 | `periodic_tasks.py` | 闭关、引道、问道、裂缝、启阵、助阵 | ✅ 完成 |
| 观星台 | `star_observation.py` | 观星、牵引、收集、安抚 | ✅ 完成 |
| 小药园 | `herb_garden.py` | 维护、采药、播种、兑换 | ✅ 完成 |
| 元婴任务 | `yuanying_tasks.py` | 元婴状态查询、出窍 | ✅ 完成 |
| 活动管理 | `activity_manager.py` | 活动识别与响应 | ✅ 完成 |
| 小智AI | `xiaozhi_client.py` | WebSocket连接、AI对话 | ✅ 完成 |
| 冷却解析 | `cooldown_parser.py` | 智能时间解析 | ✅ 完成 |
| 日志系统 | `logger.py` | 按账号分离日志 | ✅ 完成 |

### 2.3 数据流

```
用户命令 → CLI解析 → Worker初始化 → 模块启动
                                        ↓
频道消息 → Telegram Client → Worker接收 → 消息分类
                                        ↓
                         ┌──────────────┴──────────────┐
                         │     消息分类管线             │
                         │  1. Daily (每日)            │
                         │  2. Star (星宫)             │
                         │  3. Herb (药园)             │
                         │  4. Periodic (周期)         │
                         │  5. YuanYing (元婴)         │
                         │  6. Activity (活动)         │
                         │  7. AI (对话)               │
                         └──────────────┬──────────────┘
                                        ↓
                         命令队列 (优先级+去重)
                                        ↓
                         Telegram Client 发送
                                        ↓
                         状态持久化 (JSON)
```

### 2.4 配置体系

**配置层次结构**:
1. **系统配置**: `config.json` (小智AI、网络等)
2. **安全配置**: `efuse.json` (授权、密钥等)
3. **机器人配置**: `.signer/bot_configs/<name>/config.json`
4. **签到配置**: `.signer/signs/<name>/config.json`
5. **监控配置**: `.signer/monitors/<name>/config.json`

**配置管理特点**:
- ✅ 类型安全（Pydantic）
- ✅ 配置热加载
- ✅ 环境变量支持
- ✅ 配置导入导出

---

## 3. 功能完善情况

### 3.1 核心功能矩阵

| 功能模块 | 子功能 | 实现状态 | 测试覆盖 | 文档完整性 |
|---------|--------|---------|---------|----------|
| **账号管理** | | | | |
| - Session管理 | ✅ | 100% | ✅ | ✅ |
| - 多账号支持 | ✅ | 100% | ✅ | ✅ |
| - 代理配置 | ✅ | 100% | ⚠️ | ✅ |
| **签到系统** | | | | |
| - 定时签到 | ✅ | 100% | ✅ | ✅ |
| - 多动作流 | ✅ | 100% | ✅ | ✅ |
| - AI识图点击 | ✅ | 100% | ⚠️ | ✅ |
| - 计算题回答 | ✅ | 100% | ⚠️ | ✅ |
| **监控系统** | | | | |
| - 消息监控 | ✅ | 100% | ✅ | ✅ |
| - 规则匹配 | ✅ | 100% | ✅ | ✅ |
| - 自动回复 | ✅ | 100% | ✅ | ✅ |
| - 外部转发 | ✅ | 100% | ⚠️ | ✅ |
| **机器人系统** | | | | |
| - 每日任务 | ✅ | 100% | ✅ | ✅ |
| - 周期任务 | ✅ | 100% | ✅ | ✅ |
| - 观星台 | ✅ | 100% | ✅ | ✅ |
| - 小药园 | ✅ | 100% | ✅ | ✅ |
| - 元婴任务 | ✅ | 100% | ✅ | ✅ |
| - 活动管理 | ✅ | 100% | ✅ | ✅ |
| - 小智AI | ✅ | 100% | ✅ | ✅ |
| **基础设施** | | | | |
| - 冷却解析 | ✅ | 100% | ✅ | ✅ |
| - 日志系统 | ✅ | 100% | ✅ | ✅ |
| - 状态持久化 | ✅ | 100% | ⚠️ | ✅ |
| - 配置管理 | ✅ | 100% | ✅ | ✅ |

**图例**:
- ✅ 完整/覆盖良好
- ⚠️ 部分/需要改进
- ❌ 缺失/未实现

### 3.2 已完成的重要特性

#### 3.2.1 模块化架构 ✅
- 7个独立的业务逻辑模块
- 清晰的模块边界和职责
- 易于扩展和维护

#### 3.2.2 冷却系统 ✅
- 智能冷却时间解析（支持"12小时30分钟"格式）
- 配置化的冷却常量
- 自动冷却管理和调度
- 45+ 测试用例覆盖

#### 3.2.3 日志系统 ✅
- 按账号分离日志 (`logs/<account>/`)
- 日志轮转和归档
- 结构化日志标签
- 多级别日志支持

#### 3.2.4 状态管理 ✅
- JSON 文件持久化
- 原子写入保证一致性
- 断点续传支持
- 状态版本管理

#### 3.2.5 小智AI集成 ✅
- WebSocket 实时连接
- 自动重连机制
- 活动问答集成
- 聊天AI互动

### 3.3 待完善的功能

#### 3.3.1 测试覆盖 ⚠️
- 集成测试覆盖不足
- 缺少端到端测试
- 缺少性能测试
- Mock 层次不够完整

#### 3.3.2 错误处理 ⚠️
- 部分边界情况未处理
- 错误恢复策略需要完善
- 告警机制缺失

#### 3.3.3 监控与可观测性 ⚠️
- 缺少 Metrics 收集
- 缺少健康检查接口
- 缺少性能追踪

---

## 4. 文档组织现状

### 4.1 当前文档列表

| 文档 | 类型 | 主要内容 | 状态 | 建议 |
|------|------|---------|------|------|
| `README.md` | 主文档 | 项目介绍、快速开始、使用指南 | ✅ 最新 | 保留 |
| `README_EN.md` | 主文档 | 英文版README | ✅ 最新 | 保留 |
| `ARCHITECTURE.md` | 架构 | 系统架构设计（v1.1） | ✅ 最新 | **保留** |
| `PROJECT_ARCHITECTURE.md` | 架构 | 项目架构详解 | ⚠️ 重复 | 合并到ARCHITECTURE.md |
| `ENTERPRISE_TODO.md` | 规划 | 企业级改进建议 | ✅ 最新 | **保留** |
| `INTEGRATION_STATUS.md` | 状态 | 集成状态报告 | ✅ 最新 | **保留** |
| `BOT_USAGE_GUIDE.md` | 指南 | 机器人使用指南 | ✅ 最新 | **保留** |
| `BOT_TESTING_GUIDE.md` | 指南 | 测试指南 | ✅ 最新 | **保留** |
| `COOLDOWN_RULES.md` | 规范 | 冷却规则说明 | ✅ 最新 | **保留** |
| `YUANYING_INTEGRATION.md` | 指南 | 元婴集成说明 | ✅ 最新 | **保留** |
| `活动回复词.md` | 规范 | 活动响应规范 | ✅ 最新 | **保留** |
| `IMPLEMENTATION_SUMMARY.md` | 总结 | 实现总结V1 | ❌ 过时 | **删除** |
| `IMPLEMENTATION_SUMMARY_V2.md` | 总结 | 实现总结V2 | ❌ 过时 | **删除** |
| `IMPLEMENTATION_SUMMARY_V3.md` | 总结 | 实现总结V3 | ⚠️ 部分过时 | 合并到INTEGRATION_STATUS |
| `IMPLEMENTATION_NOTES.md` | 笔记 | 实现笔记 | ❌ 过时 | **删除** |
| `docker/README.md` | 指南 | Docker使用说明 | ✅ 最新 | 保留 |

### 4.2 文档问题分析

#### 问题 1: 文档过多且重复 ⚠️

**症状**:
- 4个 IMPLEMENTATION 文档存在内容重叠
- 2个 ARCHITECTURE 文档（ARCHITECTURE.md 和 PROJECT_ARCHITECTURE.md）内容部分重复
- 信息分散，不易查找

**影响**:
- 维护成本高（需要同步更新多个文档）
- 容易产生信息不一致
- 新用户困惑，不知道看哪个

**建议行动**:
1. 删除过时的 IMPLEMENTATION_SUMMARY*.md 和 IMPLEMENTATION_NOTES.md
2. 将 PROJECT_ARCHITECTURE.md 的有效内容合并到 ARCHITECTURE.md
3. 保持单一真实来源（Single Source of Truth）

#### 问题 2: 文档导航不清晰 ⚠️

**症状**:
- README.md 虽然提及了一些文档，但没有完整的文档地图
- 缺少"新手应该读什么"的明确指引

**建议行动**:
1. 在 README.md 添加"📚 文档导航"章节
2. 按角色（新手/开发者/维护者）组织文档推荐

### 4.3 推荐的文档结构

```
📚 文档体系（推荐）

入门级:
├─ README.md                    # 项目介绍和快速开始
├─ README_EN.md                 # English version
└─ BOT_USAGE_GUIDE.md          # 机器人使用指南（新手必读）

使用指南:
├─ BOT_TESTING_GUIDE.md        # 测试指南
├─ YUANYING_INTEGRATION.md     # 元婴功能指南
└─ docker/README.md            # Docker部署指南

架构与设计:
├─ ARCHITECTURE.md             # 完整架构设计（开发者必读）
├─ COOLDOWN_RULES.md          # 冷却规则详解
└─ 活动回复词.md               # 活动响应规范

项目管理:
├─ INTEGRATION_STATUS.md       # 功能集成状态
├─ ENTERPRISE_TODO.md          # 企业级改进建议
└─ PROJECT_ANALYSIS.md         # 本文档：项目分析报告
```

---

## 5. 企业级建议与TODO

### 5.1 优先级分级

| 优先级 | 说明 | 时间框架 |
|-------|------|---------|
| P0 | 紧急且重要，影响核心功能 | 立即（1周内） |
| P1 | 重要，提升质量和稳定性 | 短期（1个月内） |
| P2 | 增强，改善用户体验 | 中期（3个月内） |
| P3 | 可选，锦上添花 | 长期（6个月内） |

### 5.2 代码质量改进

#### P0: 关键错误处理增强

**现状**: 部分异常捕获不够精确，可能导致进程意外退出

**任务**:
- [ ] 审查所有 `try-except` 块，避免过度捕获
- [ ] 为关键函数添加超时保护
- [ ] 实现优雅关闭机制（SIGTERM/SIGINT处理）
- [ ] 添加崩溃后自动重启逻辑

**验收标准**:
- 所有网络调用有超时设置
- 关键任务失败不影响其他任务
- 进程可以优雅退出

#### P1: 类型注解完善

**现状**: 约60%的函数有类型注解，但不完整

**任务**:
- [ ] 为所有公共函数添加完整类型注解
- [ ] 引入 `mypy` 静态类型检查
- [ ] 配置 pre-commit hook 强制类型检查
- [ ] 添加 `py.typed` 标记支持类型检查

**验收标准**:
- `mypy --strict` 无错误
- 100% 公共API有类型注解

#### P1: 代码复杂度控制

**现状**: 部分函数超过50行，嵌套层级较深

**任务**:
- [ ] 使用 `radon` 检测复杂度
- [ ] 重构 McCabe 复杂度 > 10 的函数
- [ ] 提取可复用的辅助函数
- [ ] 添加复杂度检查到 CI

**目标**:
- 函数长度 < 50 行
- McCabe 复杂度 < 10
- 嵌套深度 < 4

#### P2: 文档字符串规范

**任务**:
- [ ] 为所有公共函数添加 docstring
- [ ] 统一使用 Google 风格
- [ ] 集成 `pydocstyle` 检查
- [ ] 使用 Sphinx 自动生成 API 文档

### 5.3 测试覆盖提升

#### P0: 关键路径集成测试

**现状**: 单元测试较完善，但缺少集成测试

**任务**:
- [ ] 添加每日任务完整流程测试
- [ ] 添加周期任务调度测试
- [ ] 添加消息分类管线集成测试
- [ ] 添加状态恢复测试

**目标**: 核心流程 100% 集成测试覆盖

#### P1: Mock 框架完善

**任务**:
- [ ] 封装 Telegram Client Mock
- [ ] 封装时间 Mock 工具
- [ ] 封装文件系统 Mock
- [ ] 提供测试夹具库

#### P2: 测试覆盖率目标

**任务**:
- [ ] 集成 `pytest-cov` 生成覆盖率报告
- [ ] 设置覆盖率目标 85%+
- [ ] 在 CI 中强制覆盖率检查
- [ ] 添加覆盖率徽章到 README

### 5.4 可观测性增强

#### P1: 结构化日志

**现状**: 日志是纯文本格式，不易分析

**任务**:
- [ ] 引入 `structlog` 结构化日志
- [ ] 添加 correlation ID 追踪请求链路
- [ ] 支持 JSON 格式日志输出
- [ ] 集成日志收集系统（如 ELK）

#### P1: Metrics 收集

**任务**:
- [ ] 添加任务执行统计（成功/失败/耗时）
- [ ] 添加消息处理统计
- [ ] 添加 API 调用统计
- [ ] 支持 Prometheus 格式导出

#### P2: 健康检查

**任务**:
- [ ] 添加 HTTP 健康检查接口
- [ ] 检查 Telegram 连接状态
- [ ] 检查任务队列状态
- [ ] 检查磁盘空间和内存使用

#### P2: 分布式追踪

**任务**:
- [ ] 集成 OpenTelemetry
- [ ] 追踪消息处理全链路
- [ ] 追踪外部 API 调用
- [ ] 集成 Jaeger/Zipkin

### 5.5 安全加固

#### P0: 敏感信息保护

**任务**:
- [ ] 审查所有日志，避免记录敏感信息
- [ ] 实现配置文件加密存储
- [ ] 使用密钥管理服务（如 Vault）
- [ ] 添加 `.gitignore` 防止泄露

#### P1: 输入验证

**任务**:
- [ ] 验证所有外部输入（配置、消息）
- [ ] 使用 Pydantic 验证器
- [ ] 添加 SQL 注入防护（如果使用数据库）
- [ ] 添加路径遍历防护

#### P2: 权限控制

**任务**:
- [ ] 实现基于角色的访问控制（RBAC）
- [ ] 为敏感操作添加审计日志
- [ ] 实现操作频率限制
- [ ] 添加 IP 白名单支持

### 5.6 性能优化

#### P1: 异步优化

**任务**:
- [ ] 审查所有阻塞调用
- [ ] 使用 `asyncio.gather` 并发执行
- [ ] 添加连接池
- [ ] 优化大数据量处理

#### P2: 缓存策略

**任务**:
- [ ] 添加配置缓存
- [ ] 添加频道信息缓存
- [ ] 实现 LRU 缓存
- [ ] 添加缓存失效机制

#### P2: 资源管理

**任务**:
- [ ] 添加内存使用监控
- [ ] 实现日志文件自动清理
- [ ] 添加状态文件压缩
- [ ] 优化会话文件存储

### 5.7 CI/CD 集成

#### P1: 持续集成

**任务**:
- [ ] 配置 GitHub Actions 自动测试
- [ ] 添加 lint 检查（ruff, mypy）
- [ ] 添加代码覆盖率报告
- [ ] 添加依赖安全扫描

#### P2: 持续部署

**任务**:
- [ ] 自动构建 Docker 镜像
- [ ] 推送到容器仓库
- [ ] 自动发布 PyPI 包
- [ ] 添加发布说明自动生成

#### P2: 质量门禁

**任务**:
- [ ] 设置最低测试覆盖率 85%
- [ ] 设置最大代码复杂度 10
- [ ] 禁止 TODO/FIXME 合并
- [ ] 要求 PR 必须通过所有检查

### 5.8 文档完善

#### P1: API 文档

**任务**:
- [ ] 使用 Sphinx 生成 API 文档
- [ ] 托管到 Read the Docs
- [ ] 添加代码示例
- [ ] 添加常见问题（FAQ）

#### P1: 贡献指南

**任务**:
- [ ] 创建 CONTRIBUTING.md
- [ ] 说明开发环境搭建
- [ ] 说明代码规范
- [ ] 说明 PR 流程

#### P2: 变更日志

**任务**:
- [ ] 创建 CHANGELOG.md
- [ ] 遵循 Keep a Changelog 格式
- [ ] 记录所有版本变更
- [ ] 添加迁移指南

---

## 6. 维护指南

### 6.1 日常维护任务

#### 每日
- [ ] 检查 CI 构建状态
- [ ] 检查错误日志
- [ ] 审查新 Issues
- [ ] 审查新 Pull Requests

#### 每周
- [ ] 运行完整测试套件
- [ ] 检查依赖更新
- [ ] 审查性能指标
- [ ] 清理过期日志

#### 每月
- [ ] 更新依赖版本
- [ ] 审查安全漏洞
- [ ] 更新文档
- [ ] 发布新版本

### 6.2 代码审查检查清单

#### 功能
- [ ] 代码实现符合需求
- [ ] 边界情况已处理
- [ ] 错误处理完善
- [ ] 性能可接受

#### 代码质量
- [ ] 代码清晰易读
- [ ] 命名符合规范
- [ ] 无重复代码
- [ ] 复杂度可接受

#### 测试
- [ ] 有单元测试
- [ ] 有集成测试
- [ ] 测试覆盖充分
- [ ] 测试可维护

#### 文档
- [ ] 有 docstring
- [ ] 有使用示例
- [ ] README 已更新
- [ ] CHANGELOG 已更新

### 6.3 发布流程

#### 1. 准备阶段
```bash
# 更新版本号
vi pyproject.toml

# 更新变更日志
vi CHANGELOG.md

# 运行完整测试
pytest tests/ -v --cov

# 检查代码质量
ruff check .
mypy tg_signer/
```

#### 2. 构建阶段
```bash
# 构建包
python -m build

# 检查包
twine check dist/*

# 本地测试
pip install dist/*.whl
```

#### 3. 发布阶段
```bash
# 创建 Git 标签
git tag -a v0.x.x -m "Release v0.x.x"
git push origin v0.x.x

# 发布到 PyPI
twine upload dist/*

# 构建 Docker 镜像
docker build -t tg-signer:v0.x.x .
docker push tg-signer:v0.x.x
```

#### 4. 公告阶段
- 在 GitHub 发布 Release Notes
- 更新文档网站
- 在社区发布公告

### 6.4 故障排查指南

#### 问题: 无法连接 Telegram

**检查清单**:
1. 检查网络连接
2. 检查代理配置
3. 检查 API ID/Hash 是否正确
4. 查看日志中的错误信息

**解决方案**:
```bash
# 测试网络连接
ping telegram.org

# 测试代理
export TG_PROXY=socks5://127.0.0.1:7890
tg-signer login
```

#### 问题: 任务不执行

**检查清单**:
1. 检查配置文件是否正确
2. 检查任务是否在冷却中
3. 检查日志中的错误
4. 检查状态文件

**解决方案**:
```bash
# 检查配置
tg-signer bot doctor <name>

# 查看日志
tail -f logs/<account>/<account>.log

# 查看状态
cat .signer/bot_configs/<name>/state.json
```

#### 问题: 内存占用高

**检查清单**:
1. 检查日志文件大小
2. 检查消息缓存
3. 检查状态文件大小
4. 检查是否有内存泄漏

**解决方案**:
```bash
# 清理日志
find logs/ -type f -name "*.log" -mtime +7 -delete

# 压缩状态文件
find .signer/ -type f -name "*.json" -exec gzip {} \;

# 监控内存
watch -n 1 'ps aux | grep tg-signer'
```

### 6.5 贡献流程

#### 1. Fork 和克隆
```bash
# Fork 项目到你的账号
# 然后克隆
git clone https://github.com/YOUR_USERNAME/tg-signer-xiaozhi.git
cd tg-signer-xiaozhi
```

#### 2. 创建功能分支
```bash
git checkout -b feature/your-feature-name
```

#### 3. 开发和测试
```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/ -v

# 检查代码质量
ruff check .
mypy tg_signer/
```

#### 4. 提交和推送
```bash
git add .
git commit -m "feat: add your feature"
git push origin feature/your-feature-name
```

#### 5. 创建 Pull Request
- 在 GitHub 上创建 PR
- 填写 PR 模板
- 等待代码审查
- 根据反馈修改

---

## 附录

### A. 依赖管理

#### 生产依赖
```toml
[project.dependencies]
kurigram = "~=2.2.7"
pydantic = "^2.0.0"
click = "^8.0.0"
aiofiles = "^23.0.0"
websockets = "^12.0"  # 可选
```

#### 开发依赖
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-asyncio>=0.21.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]
```

### B. 配置示例

#### 最小配置
```json
{
  "chat_id": -1001234567890,
  "name": "测试频道",
  "daily": {
    "enable_sign_in": true
  }
}
```

#### 完整配置
参考 `example_bot_config.json`

### C. 常用命令

```bash
# 开发
pip install -e ".[dev]"
pytest tests/ -v
ruff check .
mypy tg_signer/

# 使用
tg-signer login
tg-signer bot init
tg-signer bot config my_bot
tg-signer bot run my_bot

# 调试
tg-signer --log-level debug bot run my_bot
tg-signer bot doctor my_bot
```

### D. 相关链接

- **GitHub 仓库**: https://github.com/AlexYao521/tg-signer-xiaozhi
- **PyPI**: https://pypi.org/project/tg-signer/
- **Telegram API**: https://core.telegram.org/
- **Pyrogram 文档**: https://docs.pyrogram.org/

---

**文档版本**: 1.0  
**最后更新**: 2024  
**维护者**: AlexYao521
