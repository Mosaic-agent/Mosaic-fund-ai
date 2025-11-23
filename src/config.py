"""
Mosaic Vault - Configuration Management
Handles environment variables and system configuration.
"""

import os
from typing import Dict, Optional, Union
from dataclasses import dataclass
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

@dataclass
class ZerodhaConfig:
    """Zerodha API configuration"""
    api_key: str
    api_secret: str
    user_id: str
    password: str
    totp_secret: str
    access_token: Optional[str] = None

@dataclass 
class GeminiConfig:
    """Gemini AI configuration"""
    api_key: Optional[str] = None
    cli_command: str = "gemini"
    rate_limit_delay: float = 1.0

@dataclass
class NotificationConfig:
    """Notification system configuration"""
    whatsapp_number: Optional[str] = None
    callmebot_api_key: Optional[str] = None
    enabled: bool = False

@dataclass
class RiskConfig:
    """Risk management configuration"""
    floor_ratio: float = 0.9
    multiplier_green: float = 5.0
    multiplier_yellow: float = 3.0
    multiplier_red: float = 1.0
    max_drawdown: float = 10.0
    max_position_size: float = 10.0
    max_sector_concentration: float = 25.0

@dataclass
class SystemConfig:
    """System operational configuration"""
    database_path: str = "data/vault.db"
    dashboard_refresh: int = 60
    log_level: str = "INFO"
    mock_mode: bool = False
    debug_mode: bool = False
    market_open_time: str = "09:15"
    market_close_time: str = "15:30"
    risk_audit_frequency: int = 15
    price_drop_threshold: float = 5.0

class Config:
    """
    Main configuration class for Mosaic Vault
    Loads and validates all configuration from environment variables
    """
    
    def __init__(self):
        self.zerodha = self._load_zerodha_config()
        self.gemini = self._load_gemini_config() 
        self.notifications = self._load_notification_config()
        self.risk = self._load_risk_config()
        self.system = self._load_system_config()
        
        # Validate configuration
        self._validate_config()
    
    def _load_zerodha_config(self) -> ZerodhaConfig:
        """Load Zerodha configuration from environment"""
        return ZerodhaConfig(
            api_key=os.getenv('KITE_API_KEY', ''),
            api_secret=os.getenv('KITE_API_SECRET', ''),
            user_id=os.getenv('KITE_USER_ID', ''),
            password=os.getenv('KITE_PASSWORD', ''),
            totp_secret=os.getenv('KITE_TOTP_SECRET', ''),
            access_token=os.getenv('KITE_ACCESS_TOKEN')
        )
    
    def _load_gemini_config(self) -> GeminiConfig:
        """Load Gemini configuration from environment"""
        return GeminiConfig(
            api_key=os.getenv('GEMINI_API_KEY'),
            cli_command=os.getenv('GEMINI_CLI_COMMAND', 'gemini'),
            rate_limit_delay=float(os.getenv('GEMINI_RATE_LIMIT', '1.0'))
        )
    
    def _load_notification_config(self) -> NotificationConfig:
        """Load notification configuration from environment"""
        whatsapp_number = os.getenv('WHATSAPP_NUMBER')
        callmebot_key = os.getenv('CALLMEBOT_API_KEY')
        
        return NotificationConfig(
            whatsapp_number=whatsapp_number,
            callmebot_api_key=callmebot_key,
            enabled=bool(whatsapp_number and callmebot_key)
        )
    
    def _load_risk_config(self) -> RiskConfig:
        """Load risk management configuration from environment"""
        return RiskConfig(
            floor_ratio=float(os.getenv('RISK_FLOOR_RATIO', '0.9')),
            multiplier_green=float(os.getenv('CPPI_MULTIPLIER_GREEN', '5.0')),
            multiplier_yellow=float(os.getenv('CPPI_MULTIPLIER_YELLOW', '3.0')),
            multiplier_red=float(os.getenv('CPPI_MULTIPLIER_RED', '1.0')),
            max_drawdown=float(os.getenv('MAX_DRAWDOWN', '10.0')),
            max_position_size=float(os.getenv('MAX_POSITION_SIZE', '10.0')),
            max_sector_concentration=float(os.getenv('MAX_SECTOR_CONCENTRATION', '25.0'))
        )
    
    def _load_system_config(self) -> SystemConfig:
        """Load system configuration from environment"""
        return SystemConfig(
            database_path=os.getenv('DATABASE_PATH', 'data/vault.db'),
            dashboard_refresh=int(os.getenv('DASHBOARD_REFRESH', '60')),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            mock_mode=os.getenv('MOCK_MODE', 'false').lower() == 'true',
            debug_mode=os.getenv('DEBUG_MODE', 'false').lower() == 'true',
            market_open_time=os.getenv('MARKET_OPEN_TIME', '09:15'),
            market_close_time=os.getenv('MARKET_CLOSE_TIME', '15:30'),
            risk_audit_frequency=int(os.getenv('RISK_AUDIT_FREQUENCY', '15')),
            price_drop_threshold=float(os.getenv('PRICE_DROP_THRESHOLD', '5.0'))
        )
    
    def _validate_config(self) -> None:
        """Validate configuration and log warnings for missing values"""
        logger = logging.getLogger(__name__)
        
        # Check required Zerodha credentials
        if not all([
            self.zerodha.api_key,
            self.zerodha.api_secret, 
            self.zerodha.user_id,
            self.zerodha.password,
            self.zerodha.totp_secret
        ]):
            logger.warning("Zerodha credentials incomplete - running in mock mode")
            self.system.mock_mode = True
        
        # Check Gemini availability
        if not self.gemini.api_key:
            logger.info("Gemini API key not set - using CLI authentication")
        
        # Check notification setup
        if not self.notifications.enabled:
            logger.info("Notifications disabled - WhatsApp credentials not configured")
        
        # Validate risk parameters
        if self.risk.floor_ratio < 0.8 or self.risk.floor_ratio > 0.95:
            logger.warning(f"Floor ratio {self.risk.floor_ratio} outside recommended range (0.8-0.95)")
        
        if self.risk.max_drawdown < 5 or self.risk.max_drawdown > 20:
            logger.warning(f"Max drawdown {self.risk.max_drawdown}% outside typical range (5-20%)")
        
        logger.info("Configuration validation complete")
    
    def get_database_url(self) -> str:
        """Get SQLite database URL"""
        return f"sqlite:///{self.system.database_path}"
    
    def is_market_hours(self) -> bool:
        """Check if current time is within market hours"""
        from datetime import datetime, time
        
        now = datetime.now().time()
        open_time = datetime.strptime(self.system.market_open_time, "%H:%M").time()
        close_time = datetime.strptime(self.system.market_close_time, "%H:%M").time()
        
        return open_time <= now <= close_time
    
    def to_dict(self) -> Dict:
        """Convert configuration to dictionary for serialization"""
        return {
            'zerodha': {
                'api_key': self.zerodha.api_key[:8] + "..." if self.zerodha.api_key else None,
                'configured': bool(self.zerodha.api_key and self.zerodha.api_secret)
            },
            'gemini': {
                'api_key_configured': bool(self.gemini.api_key),
                'cli_command': self.gemini.cli_command
            },
            'notifications': {
                'enabled': self.notifications.enabled,
                'whatsapp_configured': bool(self.notifications.whatsapp_number)
            },
            'risk': {
                'floor_ratio': self.risk.floor_ratio,
                'max_drawdown': self.risk.max_drawdown,
                'max_position_size': self.risk.max_position_size
            },
            'system': {
                'mock_mode': self.system.mock_mode,
                'debug_mode': self.system.debug_mode,
                'database_path': self.system.database_path
            }
        }

# Global configuration instance
config = Config()

# Convenience functions
def get_config() -> Config:
    """Get the global configuration instance"""
    return config

def is_mock_mode() -> bool:
    """Check if running in mock mode"""
    return config.system.mock_mode

def get_database_path() -> str:
    """Get database file path"""
    return config.system.database_path

def setup_logging() -> None:
    """Setup logging configuration"""
    level = getattr(logging, config.system.log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    if config.system.debug_mode:
        logging.getLogger().setLevel(logging.DEBUG)

if __name__ == "__main__":
    """Test configuration loading"""
    print("Mosaic Vault Configuration Test")
    print("=" * 40)
    
    cfg = get_config()
    config_dict = cfg.to_dict()
    
    import json
    print(json.dumps(config_dict, indent=2))
    
    print(f"\\nMock mode: {is_mock_mode()}")
    print(f"Market hours: {cfg.is_market_hours()}")
    print(f"Database path: {get_database_path()}")