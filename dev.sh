#!/bin/bash
# 开发模式运行脚本 (Linux/Mac)
# 
# 使用方法：
#   ./dev.sh -a 账号名 bot run 配置名
#   ./dev.sh version
#   ./dev.sh bot init
#
# 这个脚本会设置 PYTHONPATH 确保运行的是本地最新代码

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 设置 PYTHONPATH
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH}"

# 运行 tg-signer，传递所有参数
tg-signer "$@"
