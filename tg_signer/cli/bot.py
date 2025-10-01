"""
CLI commands for channel automation bot
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

import click

from tg_signer.bot_config import BotConfig, create_default_bot_config
from tg_signer.bot_worker import ChannelBot

logger = logging.getLogger("tg-signer.bot.cli")


@click.group(name="bot", help="频道自动化机器人管理")
def bot_cli():
    """Channel automation bot management"""
    pass


@bot_cli.command(name="run", help="运行频道自动化机器人")
@click.argument("config_name")
@click.option(
    "--xiaozhi-config",
    "-x",
    default=None,
    help="小智AI配置文件路径（默认: config/config.json）",
    type=click.Path()
)
@click.option(
    "--ai",
    is_flag=True,
    default=False,
    help="启用小智AI聊天互动（不影响小智客户端初始化，只控制聊天消息AI互动）"
)
@click.pass_obj
def run_bot(obj, config_name: str, xiaozhi_config: Optional[str], ai: bool):
    """Run channel automation bot"""
    workdir = Path(obj["workdir"])
    config_file = workdir / "bot_configs" / f"{config_name}.json"
    
    if not config_file.exists():
        click.echo(f"配置文件不存在: {config_file}")
        click.echo(f"请先使用 'tg-signer bot config {config_name}' 创建配置")
        return
    
    try:
        # Load bot configuration
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        bot_config = BotConfig(**config_data)
        
        # Override AI settings if --ai flag is provided
        if ai:
            # Enable AI chat interaction
            if not bot_config.xiaozhi_ai.authorized_users:
                click.echo("警告: --ai 标志已设置，但配置中未指定授权用户")
        else:
            # Disable AI chat interaction (but still initialize xiaozhi client for activity responses)
            bot_config.xiaozhi_ai.trigger_keywords = []
        
        # Determine xiaozhi config path
        if xiaozhi_config is None:
            # Try config folder first
            config_dir = workdir / "config"
            if (config_dir / "config.json").exists():
                xiaozhi_config = str(config_dir / "config.json")
            elif Path("config.json").exists():
                xiaozhi_config = "config.json"
            else:
                xiaozhi_config = str(config_dir / "config.json")  # Default, may not exist
        
        # Create and run bot
        bot = ChannelBot(
            config=bot_config,
            account=obj["account"],
            proxy=obj["proxy"],
            session_dir=obj["session_dir"],
            workdir=str(workdir / "bot_workdir"),
            session_string=obj["session_string"],
            in_memory=obj["in_memory"],
            xiaozhi_config_path=xiaozhi_config
        )
        
        ai_status = "启用" if ai and bot_config.xiaozhi_ai.authorized_users else "禁用"
        click.echo(f"启动机器人: {config_name} (频道: {bot_config.chat_id})")
        click.echo(f"小智AI聊天互动: {ai_status}")
        
        # Run bot
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot.run())
        
    except Exception as e:
        if "TG_API_ID and TG_API_HASH must be set" in str(e):
            click.echo(f"运行机器人失败: {e}")
            click.echo("\n请配置 Telegram API 凭据：")
            click.echo("1. 使用 'tg-signer bot init' 命令初始化配置")
            click.echo("2. 或设置环境变量: export TG_API_ID='...' 和 export TG_API_HASH='...'")
            click.echo("3. 或在 .env 文件中配置 TG_API_ID 和 TG_API_HASH")
        else:
            click.echo(f"运行机器人失败: {e}")
        logger.error(f"Failed to run bot: {e}", exc_info=True)
        raise click.Abort()


@bot_cli.command(name="config", help="配置频道自动化机器人（交互式）")
@click.argument("config_name")
@click.pass_obj
def config_bot(obj, config_name: str):
    """Configure channel automation bot (interactive)"""
    workdir = Path(obj["workdir"])
    config_dir = workdir / "bot_configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / f"{config_name}.json"
    
    click.echo(f"\n=== 配置频道自动化机器人: {config_name} ===\n")
    
    # Check if config exists
    if config_file.exists():
        if not click.confirm(f"配置 '{config_name}' 已存在，是否覆盖？"):
            return
    
    # Interactive configuration
    chat_id = click.prompt("频道ID (例如: -1001234567890)", type=int)
    name = click.prompt("频道名称", default=f"频道_{chat_id}")
    
    # Daily tasks
    click.echo("\n--- 每日任务配置 ---")
    enable_sign_in = click.confirm("启用每日点卯？", default=True)
    enable_transmission = click.confirm("启用传功？", default=True)
    enable_greeting = click.confirm("启用问安？", default=False)
    
    # Periodic tasks
    click.echo("\n--- 周期任务配置 ---")
    enable_qizhen = click.confirm("启用启阵？", default=True)
    enable_zhuzhen = click.confirm("启用助阵？", default=True)
    enable_wendao = click.confirm("启用问道？", default=True)
    enable_yindao = click.confirm("启用引道？", default=True)
    enable_yuanying = click.confirm("启用元婴？", default=True)
    enable_rift_explore = click.confirm("启用裂缝探索？", default=True)
    
    # Star observation
    click.echo("\n--- 观星台配置 ---")
    star_enabled = click.confirm("启用观星台功能？", default=True)
    default_star = "天雷星"
    if star_enabled:
        default_star = click.prompt("默认星辰", default="天雷星")
    
    # Herb garden
    click.echo("\n--- 小药园配置 ---")
    herb_enabled = click.confirm("启用小药园自动化？", default=False)
    
    # Xiaozhi AI
    click.echo("\n--- 小智AI配置 ---")
    click.echo("说明：此处配置授权用户，实际启用由运行时 --ai 标志控制")
    click.echo("     不使用 --ai：仅用于活动问答（如天机考验）")
    click.echo("     使用 --ai：额外启用聊天消息AI互动")
    xiaozhi_enabled = click.confirm("是否配置授权用户？", default=False)
    authorized_users = []
    if xiaozhi_enabled:
        user_input = click.prompt(
            "授权用户ID (用逗号分隔，例如: 123456,789012)",
            default=""
        )
        if user_input:
            authorized_users = [int(uid.strip()) for uid in user_input.split(",")]
    
    # Create configuration
    config_data = {
        "chat_id": chat_id,
        "name": name,
        "daily": {
            "enable_sign_in": enable_sign_in,
            "enable_transmission": enable_transmission,
            "enable_greeting": enable_greeting
        },
        "periodic": {
            "enable_qizhen": enable_qizhen,
            "enable_zhuzhen": enable_zhuzhen,
            "enable_wendao": enable_wendao,
            "enable_yindao": enable_yindao,
            "enable_yuanying": enable_yuanying,
            "enable_rift_explore": enable_rift_explore
        },
        "star_observation": {
            "enabled": star_enabled,
            "default_star": default_star,
            "plate_count": 5,
            "sequence": ["天雷星", "烈阳星", "玄冰星"]
        },
        "herb_garden": {
            "enabled": herb_enabled
        },
        "xiaozhi_ai": {
            "authorized_users": authorized_users,
            "filter_keywords": [],
            "blacklist_users": [],
            "debug": False
        },
        "activity": {
            "enabled": True,
            "rules_extra": []
        }
    }
    
    # Save configuration
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)
    
    click.echo(f"\n配置已保存到: {config_file}")
    click.echo(f"\n使用以下命令运行机器人:")
    click.echo(f"  # 不启用AI聊天互动（仅活动问答）：")
    click.echo(f"  tg-signer -a <账号名> bot run {config_name}")
    click.echo(f"\n  # 启用AI聊天互动：")
    click.echo(f"  tg-signer -a <账号名> bot run {config_name} --ai")
    click.echo(f"\n注意：-a 是全局选项，必须放在 bot 之前！")


@bot_cli.command(name="init", help="智能初始化tg-signer配置（包含小智AI配置）")
@click.pass_obj
def init_bot(obj):
    """Initialize tg-signer configuration intelligently"""
    import os
    import shutil
    
    workdir = Path(obj["workdir"])
    click.echo(f"\n=== tg-signer 智能配置初始化 ===\n")
    click.echo(f"工作目录: {workdir}\n")
    
    # 1. Create directory structure
    click.echo("1. 创建目录结构...")
    config_dir = workdir / "config"
    bot_configs_dir = workdir / "bot_configs"
    bot_workdir = workdir / "bot_workdir"
    
    config_dir.mkdir(parents=True, exist_ok=True)
    bot_configs_dir.mkdir(parents=True, exist_ok=True)
    bot_workdir.mkdir(parents=True, exist_ok=True)
    click.echo(f"   ✓ 已创建: {config_dir}")
    click.echo(f"   ✓ 已创建: {bot_configs_dir}")
    click.echo(f"   ✓ 已创建: {bot_workdir}")
    
    # 2. Move config.json and efuse.json to config folder
    click.echo("\n2. 迁移配置文件到 config 文件夹...")
    for filename in ["config.json", "efuse.json"]:
        src = Path(filename)
        dst = config_dir / filename
        
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
            click.echo(f"   ✓ 已复制: {filename} -> {dst}")
        elif dst.exists():
            click.echo(f"   - 已存在: {dst}")
        else:
            click.echo(f"   ! 未找到: {filename}")
    
    # 3. Check/Create default Telegram API credentials
    click.echo("\n3. 配置 Telegram API 凭据...")
    env_file = workdir / ".env"
    
    api_id = os.getenv("TG_API_ID")
    api_hash = os.getenv("TG_API_HASH")
    
    if not api_id or not api_hash:
        click.echo("   未检测到 TG_API_ID 和 TG_API_HASH 环境变量")
        if click.confirm("   是否配置 Telegram API 凭据？"):
            api_id = click.prompt("   请输入 TG_API_ID", type=str)
            api_hash = click.prompt("   请输入 TG_API_HASH", type=str)
            
            # Save to .env file
            with open(env_file, 'w') as f:
                f.write(f"export TG_API_ID=\"{api_id}\"\n")
                f.write(f"export TG_API_HASH=\"{api_hash}\"\n")
            
            click.echo(f"   ✓ 已保存到: {env_file}")
            click.echo(f"   请运行: source {env_file}")
    else:
        click.echo(f"   ✓ 已配置: TG_API_ID={api_id}")
    
    # 4. Check/Configure proxy
    click.echo("\n4. 配置代理...")
    proxy = obj.get("proxy") or os.getenv("TG_PROXY")
    
    if not proxy:
        if click.confirm("   是否配置代理？"):
            proxy = click.prompt("   代理地址", default="socks5://127.0.0.1:7897")
            
            # Append to .env file
            with open(env_file, 'a') as f:
                f.write(f"export TG_PROXY=\"{proxy}\"\n")
            
            click.echo(f"   ✓ 已保存代理设置到: {env_file}")
    else:
        click.echo(f"   ✓ 已配置代理: {proxy}")
    
    # 5. Create example bot configuration
    click.echo("\n5. 创建示例机器人配置...")
    example_config = bot_configs_dir / "example.json"
    
    if not example_config.exists():
        example_data = {
            "chat_id": -1001234567890,
            "name": "示例频道",
            "daily": {
                "enable_sign_in": True,
                "enable_transmission": True,
                "enable_greeting": False
            },
            "periodic": {
                "enable_qizhen": True,
                "enable_zhuzhen": True,
                "enable_wendao": True,
                "enable_yindao": True,
                "enable_yuanying": True,
                "enable_rift_explore": True
            },
            "star_observation": {
                "enabled": True,
                "default_star": "天雷星",
                "plate_count": 5,
                "sequence": ["天雷星", "烈阳星", "玄冰星"]
            },
            "herb_garden": {
                "enabled": False
            },
            "xiaozhi_ai": {
                "authorized_users": [],
                "filter_keywords": [],
                "blacklist_users": [],
                "debug": False
            },
            "activity": {
                "enabled": True,
                "rules_extra": []
            }
        }
        
        with open(example_config, 'w', encoding='utf-8') as f:
            json.dump(example_data, f, indent=2, ensure_ascii=False)
        
        click.echo(f"   ✓ 已创建示例配置: {example_config}")
    else:
        click.echo(f"   - 示例配置已存在: {example_config}")
    
    # Summary
    click.echo("\n" + "="*60)
    click.echo("初始化完成! 下一步:")
    click.echo("="*60)
    click.echo("1. 登录 Telegram 账号:")
    click.echo(f"   tg-signer -a <账号名> login")
    click.echo()
    click.echo("2. 创建机器人配置:")
    click.echo(f"   tg-signer bot config <配置名>")
    click.echo()
    click.echo("3. 运行机器人:")
    click.echo(f"   tg-signer -a <账号名> bot run <配置名>")
    click.echo()
    click.echo("   或启用AI聊天互动:")
    click.echo(f"   tg-signer -a <账号名> bot run <配置名> --ai")
    click.echo()
    click.echo("注意：")
    click.echo("  - -a 是全局选项，必须放在 bot 之前")
    click.echo("  - --ai 标志控制是否启用小智AI聊天互动")
    click.echo("  - 不使用 --ai 时，仍会初始化小智用于活动问答")
    click.echo("="*60 + "\n")




@bot_cli.command(name="list", help="列出所有机器人配置")
@click.pass_obj
def list_bots(obj):
    """List all bot configurations"""
    workdir = Path(obj["workdir"])
    config_dir = workdir / "bot_configs"
    
    if not config_dir.exists():
        click.echo("没有找到任何机器人配置")
        return
    
    configs = list(config_dir.glob("*.json"))
    if not configs:
        click.echo("没有找到任何机器人配置")
        return
    
    click.echo(f"\n找到 {len(configs)} 个机器人配置:\n")
    
    for config_file in configs:
        config_name = config_file.stem
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            bot_config = BotConfig(**config_data)
            click.echo(f"  - {config_name}: {bot_config.name} (chat_id: {bot_config.chat_id})")
        except Exception as e:
            click.echo(f"  - {config_name}: [配置无效: {e}]")


@bot_cli.command(name="export", help="导出机器人配置")
@click.argument("config_name")
@click.option("--output", "-o", type=click.Path(), help="输出文件路径")
@click.pass_obj
def export_bot_config(obj, config_name: str, output: Optional[str]):
    """Export bot configuration"""
    workdir = Path(obj["workdir"])
    config_file = workdir / "bot_configs" / f"{config_name}.json"
    
    if not config_file.exists():
        click.echo(f"配置不存在: {config_name}")
        return
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config_data = f.read()
    
    if output:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(config_data)
        click.echo(f"配置已导出到: {output}")
    else:
        click.echo(config_data)


@bot_cli.command(name="import", help="导入机器人配置")
@click.argument("config_name")
@click.option("--input", "-i", type=click.Path(exists=True), help="输入文件路径")
@click.pass_obj
def import_bot_config(obj, config_name: str, input: Optional[str]):
    """Import bot configuration"""
    workdir = Path(obj["workdir"])
    config_dir = workdir / "bot_configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / f"{config_name}.json"
    
    if config_file.exists():
        if not click.confirm(f"配置 '{config_name}' 已存在，是否覆盖？"):
            return
    
    if input:
        with open(input, 'r', encoding='utf-8') as f:
            config_data = f.read()
    else:
        click.echo("请输入配置JSON (Ctrl+D结束):")
        config_data = click.get_text_stream("stdin").read()
    
    # Validate configuration
    try:
        data = json.loads(config_data)
        BotConfig(**data)
    except Exception as e:
        click.echo(f"配置无效: {e}")
        return
    
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_data)
    
    click.echo(f"配置已导入: {config_name}")


@bot_cli.command(name="doctor", help="检查机器人配置和环境")
@click.argument("config_name", required=False)
@click.pass_obj
def doctor(obj, config_name: Optional[str]):
    """Check bot configuration and environment"""
    click.echo("\n=== 机器人环境检查 ===\n")
    
    # Check environment variables
    import os
    api_id = os.getenv("TG_API_ID")
    api_hash = os.getenv("TG_API_HASH")
    
    if api_id and api_hash:
        click.echo("✓ Telegram API credentials found")
    else:
        click.echo("✗ Telegram API credentials not found (TG_API_ID, TG_API_HASH)")
    
    # Check session file
    workdir = Path(obj["workdir"])
    session_file = Path(obj["session_dir"]) / f"{obj['account']}.session"
    if session_file.exists():
        click.echo(f"✓ Session file found: {session_file}")
    else:
        click.echo(f"✗ Session file not found: {session_file}")
        click.echo("  请先使用 'tg-signer login' 登录")
    
    # Check xiaozhi config
    xiaozhi_config = Path("config.json")
    if xiaozhi_config.exists():
        click.echo(f"✓ Xiaozhi config found: {xiaozhi_config}")
    else:
        click.echo(f"! Xiaozhi config not found: {xiaozhi_config} (可选)")
    
    # Check efuse.json
    efuse_file = Path("efuse.json")
    if efuse_file.exists():
        click.echo(f"✓ Efuse file found: {efuse_file}")
    else:
        click.echo(f"! Efuse file not found: {efuse_file} (可选)")
    
    # Check specific config
    if config_name:
        click.echo(f"\n--- 检查配置: {config_name} ---")
        config_file = workdir / "bot_configs" / f"{config_name}.json"
        
        if not config_file.exists():
            click.echo(f"✗ 配置文件不存在: {config_file}")
        else:
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                bot_config = BotConfig(**config_data)
                click.echo(f"✓ 配置有效")
                click.echo(f"  频道ID: {bot_config.chat_id}")
                click.echo(f"  频道名称: {bot_config.name}")
                
                # Check enabled features
                features = []
                if bot_config.daily.enable_sign_in:
                    features.append("每日点卯")
                if bot_config.periodic.enable_qizhen:
                    features.append("启阵")
                if bot_config.star_observation.enabled:
                    features.append("观星台")
                if bot_config.herb_garden.enabled:
                    features.append("小药园")
                if bot_config.xiaozhi_ai.authorized_users:
                    features.append("小智AI")
                
                click.echo(f"  启用功能: {', '.join(features) if features else '无'}")
                
            except Exception as e:
                click.echo(f"✗ 配置无效: {e}")
    
    click.echo()
