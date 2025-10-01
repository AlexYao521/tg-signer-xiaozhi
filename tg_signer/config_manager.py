"""
Configuration Manager
Centralized configuration management for tg-signer bot
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger("tg-signer.config_manager")


class ConfigManager:
    """
    Centralized configuration manager.
    Handles loading and saving configuration files.
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Directory for configuration files
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Default paths
        self.xiaozhi_config_path = self.config_dir / "config.json"
        self.efuse_path = self.config_dir / "efuse.json"
        self.app_config_path = self.config_dir / "app_config.json"
        
    def get_xiaozhi_config(self) -> Optional[Dict[str, Any]]:
        """Load Xiaozhi AI configuration"""
        # Check in config directory first
        if self.xiaozhi_config_path.exists():
            return self._load_json(self.xiaozhi_config_path)
        
        # Fall back to root directory for backward compatibility
        root_config = Path("config.json")
        if root_config.exists():
            logger.warning(f"Using config.json from root directory. Consider moving to {self.config_dir}/")
            return self._load_json(root_config)
        
        logger.warning("Xiaozhi config not found")
        return None
    
    def get_efuse_config(self) -> Optional[Dict[str, Any]]:
        """Load efuse configuration"""
        # Check in config directory first
        if self.efuse_path.exists():
            return self._load_json(self.efuse_path)
        
        # Fall back to root directory for backward compatibility
        root_efuse = Path("efuse.json")
        if root_efuse.exists():
            logger.warning(f"Using efuse.json from root directory. Consider moving to {self.config_dir}/")
            return self._load_json(root_efuse)
        
        return None
    
    def get_app_config(self) -> Dict[str, Any]:
        """
        Load application configuration with defaults.
        
        Returns configuration with defaults for:
        - TG_API_ID and TG_API_HASH
        - Proxy settings
        - Other app-level settings
        """
        config = self._load_json(self.app_config_path) if self.app_config_path.exists() else {}
        
        # Apply defaults
        defaults = {
            "telegram": {
                "api_id": os.getenv("TG_API_ID"),
                "api_hash": os.getenv("TG_API_HASH"),
            },
            "proxy": {
                "enabled": True,
                "url": "socks5://127.0.0.1:7897"
            },
            "bot": {
                "min_send_interval": 1.0,
                "sign_interval": 10.0,
            },
            "logging": {
                "level": "info",
                "file": "tg-signer.log"
            }
        }
        
        # Merge with loaded config (loaded config takes precedence)
        return self._deep_merge(defaults, config)
    
    def save_app_config(self, config: Dict[str, Any]):
        """Save application configuration"""
        self._save_json(self.app_config_path, config)
    
    def get_proxy(self) -> Optional[str]:
        """Get proxy URL from configuration"""
        config = self.get_app_config()
        proxy_config = config.get("proxy", {})
        
        if proxy_config.get("enabled", True):
            proxy_url = proxy_config.get("url")
            if proxy_url:
                logger.info(f"Using proxy from config: {proxy_url}")
                return proxy_url
        
        # Fall back to environment variable
        env_proxy = os.getenv("TG_PROXY")
        if env_proxy:
            logger.info(f"Using proxy from environment: {env_proxy}")
            return env_proxy
        
        return None
    
    def get_telegram_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """
        Get Telegram API credentials.
        
        Returns:
            Tuple of (api_id, api_hash)
        """
        config = self.get_app_config()
        telegram_config = config.get("telegram", {})
        
        api_id = telegram_config.get("api_id") or os.getenv("TG_API_ID")
        api_hash = telegram_config.get("api_hash") or os.getenv("TG_API_HASH")
        
        return api_id, api_hash
    
    def _load_json(self, path: Path) -> Optional[Dict[str, Any]]:
        """Load JSON file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load {path}: {e}")
            return None
    
    def _save_json(self, path: Path, data: Dict[str, Any]):
        """Save JSON file"""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved configuration to {path}")
        except Exception as e:
            logger.error(f"Failed to save {path}: {e}")
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def create_default_xiaozhi_config(self):
        """Create default Xiaozhi configuration file"""
        default_config = {
            "SYSTEM_OPTIONS": {
                "CLIENT_ID": "default-client-id",
                "DEVICE_ID": "00:00:00:00:00:00",
                "NETWORK": {
                    "WEBSOCKET_URL": "wss://api.tenclass.net/xiaozhi/v1/",
                    "WEBSOCKET_ACCESS_TOKEN": "test-token"
                }
            },
            "TG_SIGNER": {
                "XIAOZHI_AI": {
                    "enabled": True,
                    "protocol_type": "websocket",
                    "auto_reconnect": True,
                    "max_reconnect_attempts": 5,
                    "connect_timeout": 10
                }
            }
        }
        
        self._save_json(self.xiaozhi_config_path, default_config)
        logger.info(f"Created default Xiaozhi config at {self.xiaozhi_config_path}")
    
    def create_default_app_config(self):
        """Create default application configuration file"""
        config = self.get_app_config()  # This will have defaults merged
        self.save_app_config(config)
        logger.info(f"Created default app config at {self.app_config_path}")


# Global instance
_config_manager = None


def get_config_manager(config_dir: str = "config") -> ConfigManager:
    """Get global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_dir)
    return _config_manager
