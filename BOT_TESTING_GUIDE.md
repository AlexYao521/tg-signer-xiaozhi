# 频道自动化机器人测试指南

本文档说明如何测试新添加的频道自动化机器人功能。

## 环境准备

1. **安装依赖**
```bash
pip install -e .
```

2. **设置环境变量**
```bash
export TG_API_ID="your_api_id"
export TG_API_HASH="your_api_hash"
```

3. **登录账号**（如果还没有登录）
```bash
tg-signer login
```

## 测试步骤

### 1. 检查环境

```bash
python3 -m tg_signer bot doctor
```

预期输出：
- 显示环境检查结果
- 列出缺失的配置或文件

### 2. 测试CLI命令

```bash
# 查看帮助
python3 -m tg_signer bot --help

# 应该显示以下子命令：
# - config: 配置频道自动化机器人（交互式）
# - doctor: 检查机器人配置和环境
# - export: 导出机器人配置
# - import: 导入机器人配置
# - list: 列出所有机器人配置
# - run: 运行频道自动化机器人
```

### 3. 测试配置导入

```bash
# 导入示例配置
python3 -m tg_signer bot import test_bot -i example_bot_config.json

# 列出配置
python3 -m tg_signer bot list

# 检查配置
python3 -m tg_signer bot doctor test_bot

# 导出配置
python3 -m tg_signer bot export test_bot
```

### 4. 运行集成测试

```bash
# 运行所有集成测试
python3 << 'EOF'
import sys
sys.path.insert(0, '.')

from tests.test_integration import (
    test_state_store_operations,
    test_command_queue_basic,
    test_command_queue_deduplication,
    test_bot_config_full_workflow,
    test_xiaozhi_client_creation_with_config,
    test_xiaozhi_client_disabled,
    test_bot_config_validation,
    test_example_bot_config_valid
)

tests = [
    ("State store operations", test_state_store_operations),
    ("Command queue basic", test_command_queue_basic),
    ("Command queue deduplication", test_command_queue_deduplication),
    ("Bot config full workflow", test_bot_config_full_workflow),
    ("Xiaozhi client creation", test_xiaozhi_client_creation_with_config),
    ("Xiaozhi client disabled", test_xiaozhi_client_disabled),
    ("Bot config validation", test_bot_config_validation),
    ("Example bot config valid", test_example_bot_config_valid),
]

passed = 0
for name, test_func in tests:
    try:
        test_func()
        print(f"✓ {name}")
        passed += 1
    except Exception as e:
        print(f"✗ {name}: {e}")

print(f"\n{passed}/{len(tests)} tests passed")
EOF
```

预期输出：`8/8 tests passed`

### 5. 测试配置模块导入

```bash
python3 << 'EOF'
print("Testing imports...")

from tg_signer.bot_config import BotConfig, create_default_bot_config
print("✓ bot_config imports OK")

from tg_signer.xiaozhi_client import XiaozhiClient, create_xiaozhi_client
print("✓ xiaozhi_client imports OK")

from tg_signer.bot_worker import ChannelBot, StateStore, CommandQueue
print("✓ bot_worker imports OK")

from tg_signer.cli.bot import bot_cli
print("✓ CLI imports OK")

config = create_default_bot_config(-1001234567890, "Test Channel")
print(f"✓ Config created: {config.name}")

config_dict = config.model_dump()
config2 = BotConfig(**config_dict)
print(f"✓ Config serialization OK")

print("\nAll imports working!")
EOF
```

### 6. 验证配置文件格式

```bash
python3 << 'EOF'
import json
from tg_signer.bot_config import BotConfig

# 验证示例配置文件
with open('example_bot_config.json', 'r') as f:
    config_data = json.load(f)

config = BotConfig(**config_data)
print(f"✓ Example config valid")
print(f"  Chat ID: {config.chat_id}")
print(f"  Name: {config.name}")
print(f"  Daily sign-in: {config.daily.enable_sign_in}")
print(f"  Xiaozhi AI users: {config.xiaozhi_ai.authorized_users}")
EOF
```

## 功能验证清单

- [x] bot_config 模块可以正常导入
- [x] xiaozhi_client 模块可以正常导入
- [x] bot_worker 模块可以正常导入
- [x] CLI bot 命令可以正常调用
- [x] 配置文件可以正确解析
- [x] StateStore 可以保存和加载状态
- [x] CommandQueue 支持优先级和去重
- [x] Xiaozhi客户端可以从配置创建
- [x] 所有集成测试通过

## 已知限制

1. **WebSocket 实现**: 当前 xiaozhi_client 使用占位符实现，真实的 WebSocket 连接需要安装 `websockets` 库
2. **MQTT 支持**: 暂未实现 MQTT 协议支持，仅支持 WebSocket
3. **实际运行**: 需要真实的 Telegram 账号和频道才能完整测试机器人运行

## 下一步

如需完整测试机器人运行功能，需要：

1. 有效的 Telegram 账号和 session
2. 可访问的测试频道
3. （可选）真实的小智AI服务端点

然后可以运行：
```bash
python3 -m tg_signer bot run test_bot
```

## 故障排查

如果遇到问题：

1. 检查环境变量是否设置正确
2. 使用 `--log-level debug` 查看详细日志
3. 运行 `bot doctor` 检查配置
4. 查看 `tg-signer.log` 日志文件
