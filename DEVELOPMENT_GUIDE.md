# 开发指南 (Development Guide)

## 本地开发模式

### 问题说明

当你使用 `pip install -e .` 安装后，发现每次修改代码都需要重新安装才能生效。这是因为 Python 的包缓存机制和导入系统的工作方式。

### 解决方案

有几种方法可以实现"边修改边运行"的开发体验：

#### 方法一：使用可编辑模式（推荐）

确保你使用的是可编辑安装模式（已经在使用）：

```bash
pip install -e .
```

这种模式下，Python 会创建一个指向你的源代码目录的链接，而不是复制代码。**理论上**应该能实现实时修改，但有时候会遇到模块缓存的问题。

#### 方法二：直接运行模块（推荐用于快速开发）

不使用安装的命令，直接运行 Python 模块：

```bash
# 进入项目根目录
cd /path/to/tg-signer-xiaozhi

# 直接运行模块
python -m tg_signer.cli.signer -a 账号名 bot run 配置名
```

或者创建一个开发脚本 `dev.py`:

```python
#!/usr/bin/env python
import sys
from tg_signer.cli.signer import tg_signer

if __name__ == '__main__':
    sys.exit(tg_signer())
```

然后运行：

```bash
python dev.py -a 账号名 bot run 配置名
```

#### 方法三：设置 PYTHONPATH（推荐用于持续开发）

设置 `PYTHONPATH` 环境变量，让 Python 优先从当前目录加载模块：

**Linux/Mac:**
```bash
export PYTHONPATH=/path/to/tg-signer-xiaozhi:$PYTHONPATH
tg-signer -a 账号名 bot run 配置名
```

**Windows PowerShell:**
```powershell
$env:PYTHONPATH = "C:\path\to\tg-signer-xiaozhi;$env:PYTHONPATH"
tg-signer -a 账号名 bot run 配置名
```

**Windows CMD:**
```cmd
set PYTHONPATH=C:\path\to\tg-signer-xiaozhi;%PYTHONPATH%
tg-signer -a 账号名 bot run 配置名
```

为了方便，可以创建一个启动脚本：

**dev.sh (Linux/Mac):**
```bash
#!/bin/bash
export PYTHONPATH="$(pwd):$PYTHONPATH"
tg-signer "$@"
```

**dev.ps1 (Windows PowerShell):**
```powershell
$env:PYTHONPATH = "$PWD;$env:PYTHONPATH"
tg-signer $args
```

然后使用：
```bash
# Linux/Mac
./dev.sh -a 账号名 bot run 配置名

# Windows
.\dev.ps1 -a 账号名 bot run 配置名
```

#### 方法四：使用虚拟环境并重启 Python 进程（最可靠）

如果上述方法都不行，最保险的方法是：

1. 确保使用虚拟环境
2. 修改代码后，重新启动 Python 进程（即重新运行命令）
3. 不需要重新 `pip install`，因为 `-e` 模式已经是实时链接

如果发现仍需重新安装，可能是以下原因：

1. **C扩展或编译的代码**：如果项目中有 C 扩展或需要编译的部分，需要重新安装
2. **入口点脚本**：`setup.py` 中定义的命令行入口点（console_scripts）会生成脚本，修改入口点定义后需要重新安装
3. **包元数据**：修改 `pyproject.toml` 或 `setup.py` 后需要重新安装

#### 方法五：开发时不安装，直接运行

创建一个 `run_dev.py` 在项目根目录：

```python
#!/usr/bin/env python
"""开发模式运行脚本 - 无需安装即可运行"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入并运行 CLI
from tg_signer.cli.signer import tg_signer

if __name__ == '__main__':
    sys.exit(tg_signer())
```

然后：

```bash
chmod +x run_dev.py  # Linux/Mac
python run_dev.py -a 账号名 bot run 配置名
```

### 验证是否生效

修改代码后，添加一个打印语句来验证：

```python
# 在 tg_signer/__init__.py 中添加
print(f"tg-signer {__version__} loaded from {__file__}")
```

运行命令时应该看到这个打印，如果版本号和路径是你期望的，说明生效了。

### 缓存问题处理

如果发现代码没有更新，可能是 Python 的 `__pycache__` 缓存问题：

```bash
# 清除所有 .pyc 文件
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# 或者使用 Python 清除
python -Bc "import compileall"
```

### 推荐的开发工作流

1. **初次设置**：
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   ```

2. **日常开发**：
   - 使用方法三（设置 PYTHONPATH）或方法五（直接运行脚本）
   - 修改代码后直接运行，无需重新安装
   - 如果遇到问题，清除缓存后重试

3. **测试更改**：
   ```bash
   # 运行测试确保没有破坏现有功能
   pytest tests/
   
   # 运行你的机器人
   ./dev.sh -a 账号名 bot run 配置名
   ```

## 调试技巧

### 1. 启用详细日志

```bash
tg-signer -l debug -a 账号名 bot run 配置名
```

### 2. 使用 Python 调试器

在代码中添加断点：

```python
import pdb; pdb.set_trace()
```

或使用 `breakpoint()` (Python 3.7+):

```python
breakpoint()
```

### 3. 查看账号专属日志

日志文件位置：`logs/<账号名>/<账号名>.log`

```bash
# 实时查看日志
tail -f logs/my_account/my_account.log
```

### 4. 使用 IPython 进行交互式开发

```bash
pip install ipython
ipython
```

然后在 IPython 中：

```python
from tg_signer.bot_worker import ChannelBot
# 交互式测试你的代码
```

## 常见问题

### Q: 为什么修改代码后没有生效？

A: 检查以下几点：
1. 是否使用了正确的 Python 环境（虚拟环境）？
2. 是否有多个版本的 tg-signer 安装？使用 `pip list | grep tg-signer` 检查
3. 清除 `__pycache__` 缓存
4. 确认修改的是正确的文件（检查文件路径）

### Q: 如何确认使用的是开发版本？

A: 在代码中添加版本打印或修改版本号，然后运行 `tg-signer version` 查看。

### Q: pip install -e . 和 pip install . 的区别？

A: 
- `pip install .`：将代码复制到 site-packages，修改源码不影响安装的包
- `pip install -e .`：创建链接，修改源码会影响安装的包（可编辑模式）

## 版本管理

### 更新版本号

在每次重要更改后，更新版本号：

1. 修改 `tg_signer/__init__.py` 中的 `__version__`
2. 提交代码时注明版本号变化

版本号规则：
- 主版本号（Major）：不兼容的API修改
- 次版本号（Minor）：向下兼容的功能性新增
- 修订号（Patch）：向下兼容的问题修正

例如：`0.8.1` -> `0.8.2`（bug修复）或 `0.9.0`（新功能）

### Git 工作流

```bash
# 创建功能分支
git checkout -b feature/my-feature

# 修改代码并测试
# ...

# 提交更改
git add .
git commit -m "feat: add new feature"

# 推送到远程
git push origin feature/my-feature
```

## 最佳实践

1. **使用虚拟环境**：始终在虚拟环境中开发
2. **编写测试**：为新功能添加测试用例
3. **遵循代码规范**：使用 `black` 和 `flake8` 保持代码风格一致
4. **及时提交**：小步提交，每个提交只做一件事
5. **写好注释**：特别是复杂的业务逻辑
6. **更新文档**：修改功能后同步更新相关文档

## 发布流程

当准备发布新版本时：

1. 更新版本号
2. 更新 CHANGELOG.md
3. 运行完整测试套件
4. 构建并测试包
5. 创建 Git 标签
6. 推送到 PyPI（如果发布到 PyPI）

```bash
# 构建
python -m build

# 测试安装
pip install dist/tg_signer-*.whl

# 创建标签
git tag -a v0.8.1 -m "Release version 0.8.1"
git push origin v0.8.1
```
