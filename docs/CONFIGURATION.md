# 配置文件详解

## 目录结构

```
.
├── config/                      # 配置目录
│   ├── app_config.json         # 应用配置
│   ├── config.json             # 小智 AI 配置
│   └── scripts/                # 自定义脚本
└── .signer/                     # 工作目录
    └── bot_configs/            # 脚本配置
```

## app_config.json

应用级配置：

```json
{
  "telegram": {
    "api_id": "your_api_id",
    "api_hash": "your_api_hash"
  },
  "proxy": {
    "enabled": true,
    "url": "socks5://127.0.0.1:7897"
  },
  "bot": {
    "min_send_interval": 1.0,
    "sign_interval": 10.0
  }
}
```

## 脚本配置

位置: `.signer/bot_configs/<script_name>.json`

```json
{
  "chat_id": -1001234567890,
  "name": "频道名称",
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
    "sequence": ["天雷星", "烈阳星", "玄冰星"]
  },
  "herb_garden": {
    "enabled": true,
    "default_seed": "凝血草种子",
    "seeds": {
      "凝血草种子": {
        "maturity_hours": 6,
        "exchange_batch": 10,
        "exchange_command": ".兑换种子 凝血草种子 10"
      }
    }
  },
  "xiaozhi_ai": {
    "authorized_users": [123456789],
    "trigger_keywords": ["@小智", "xiaozhi"]
  }
}
```

## 小智 AI 配置

位置: `config/config.json`

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

## 配置优先级

1. 命令行参数（如 `--ai`）
2. 配置文件
3. 环境变量
4. 默认值

## 配置验证

使用 `doctor` 命令验证配置：

```bash
tg-signer bot doctor my_script
```
