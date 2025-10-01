#!/usr/bin/env python
"""
开发模式运行脚本 - 无需安装即可运行

使用方法：
    python run_dev.py -a 账号名 bot run 配置名
    python run_dev.py version
    python run_dev.py bot init
    
这个脚本会直接从源代码目录运行，无需每次 pip install -e .
适合本地开发和调试使用。
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径的最前面，确保导入的是本地代码
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))

# 导入并运行 CLI
from tg_signer.cli.signer import tg_signer

if __name__ == '__main__':
    sys.exit(tg_signer())
