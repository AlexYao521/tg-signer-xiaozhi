# 开发模式运行脚本 (Windows PowerShell)
# 
# 使用方法：
#   .\dev.ps1 -a 账号名 bot run 配置名
#   .\dev.ps1 version
#   .\dev.ps1 bot init
#
# 这个脚本会设置 PYTHONPATH 确保运行的是本地最新代码

# 获取脚本所在目录的绝对路径
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 设置 PYTHONPATH
$env:PYTHONPATH = "$ScriptDir;$env:PYTHONPATH"

# 运行 tg-signer，传递所有参数
tg-signer $args
