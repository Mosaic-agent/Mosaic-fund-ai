#!/usr/bin/env python3
"""
Mosaic Vault - Main Application Entry Point
Orchestrates all agents and provides command-line interface.
"""

import sys
import os
import argparse
import logging
from datetime import datetime
from typing import Dict

# Add src to path
sys.path.append(os.path.dirname(__file__))

from config import get_config, setup_logging, is_mock_mode
from cli import CLI
from core.auth import get_kite_session, test_authentication
from agents.governor import Governor, audit_risk, get_vault_health  
from agents.scout import Scout, analyze_ticker, headwind_check
from dashboard import run_dashboard

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

class MosaicVault:
    """
    Main Mosaic Vault orchestrator
    Coordinates all agents and system operations
    """
    # ... (rest of the MosaicVault class remains unchanged for now)

    def __init__(self):
        self.config = get_config()
        self.kite_session = None
        self.governor = None
        self.scout = None
        self.is_running = False
        
        logger.info("Initializing Mosaic Vault...")
        self._initialize_system()
    
    def _initialize_system(self) -> None:
        """Initialize all system components"""
        try:
            # Initialize authentication
            if not is_mock_mode():
                logger.info("Initializing Kite Connect session...")
                try:
                    self.kite_session = get_kite_session()
                    logger.info("Kite session established")
                except Exception as e:
                    logger.warning(f"Kite authentication failed, switching to mock mode: {e}")
                    self.config.system.mock_mode = True
            else:
                logger.info("Running in mock mode")
            
            # Initialize agents
            self.governor = Governor(self.kite_session)
            self.scout = Scout()
            
            logger.info("Mosaic Vault initialized successfully")
            
        except Exception as e:
            logger.error(f"System initialization failed: {e}")
            raise
    
    def health_check(self) -> Dict:
        """Perform complete system health check"""
        logger.info("Performing system health check...")
        
        health = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'HEALTHY',
            'components': {}
        }
        
        # Test authentication
        try:
            if not is_mock_mode():
                auth_status = test_authentication()
                health['components']['authentication'] = 'HEALTHY' if auth_status else 'ERROR'
            else:
                health['components']['authentication'] = 'MOCK_MODE'
        except Exception as e:
            health['components']['authentication'] = f'ERROR: {str(e)}'
        
        # Test Governor
        try:
            vault_health = get_vault_health(self.kite_session)
            health['components']['governor'] = vault_health.get('vault_health', 'ERROR')
            health['portfolio_value'] = vault_health.get('portfolio_value', 0)
            health['risk_zone'] = vault_health.get('vault_health', 'UNKNOWN')
        except Exception as e:
            health['components']['governor'] = f'ERROR: {str(e)}'
        
        # Test Scout
        try:
            # Quick test analysis
            test_result = analyze_ticker('RELIANCE', 'health_check')
            health['components']['scout'] = 'HEALTHY' if test_result.get('verdict') != 'ERROR' else 'ERROR'
        except Exception as e:
            health['components']['scout'] = f'ERROR: {str(e)}'
        
        # Test database
        try:
            db_path = self.config.system.database_path
            if os.path.exists(db_path):
                health['components']['database'] = 'HEALTHY'
            else:
                health['components']['database'] = 'INITIALIZING'
        except Exception as e:
            health['components']['database'] = f'ERROR: {str(e)}'
        
        # Determine overall status
        component_statuses = [status for status in health['components'].values() 
                            if isinstance(status, str) and not status.startswith('ERROR')]
        
        if any('ERROR' in str(status) for status in health['components'].values()):
            health['overall_status'] = 'DEGRADED'
        
        logger.info(f"Health check complete: {health['overall_status']}")
        return health
    
    def run_risk_audit(self) -> Dict:
        """Run complete risk audit"""
        logger.info("Running portfolio risk audit...")
        return audit_risk(self.kite_session)
    
    def analyze_stock(self, symbol: str, trigger: str = "manual") -> Dict:
        """Analyze a specific stock using Scout"""
        logger.info(f"Analyzing {symbol}...")
        return analyze_ticker(symbol, trigger)
    
    def run_headwind_detection(self, symbol: str, price_drop: float) -> Dict:
        """Run headwind detection for stock price drop"""
        logger.info(f"Running headwind detection for {symbol} (-{price_drop}%)...")
        return headwind_check(symbol, price_drop)
    
    def start_dashboard(self, refresh_interval: int = None) -> None:
        """Start the terminal dashboard"""
        if refresh_interval is None:
            refresh_interval = self.config.system.dashboard_refresh
        
        logger.info(f"Starting dashboard (refresh: {refresh_interval}s)...")
        run_dashboard(refresh_interval)
    
    def get_status(self) -> Dict:
        """Get current system status"""
        return {
            'timestamp': datetime.now().isoformat(),
            'config': self.config.to_dict(),
            'mock_mode': is_mock_mode(),
            'market_hours': self.config.is_market_hours(),
            'agents_initialized': bool(self.governor and self.scout),
            'kite_connected': bool(self.kite_session)
        }

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Mosaic Vault - Autonomous Family Office System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py status                    # Show system status
  python main.py health                    # Run health check  
  python main.py audit                     # Run risk audit
  python main.py dashboard                 # Start dashboard
  python main.py analyze RELIANCE          # Analyze stock
  python main.py headwind TCS 5.5         # Check headwind for 5.5% drop
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show system status')
    
    # Health check command
    health_parser = subparsers.add_parser('health', help='Run system health check')
    
    # Risk audit command  
    audit_parser = subparsers.add_parser('audit', help='Run portfolio risk audit')
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser('dashboard', help='Start terminal dashboard')
    dashboard_parser.add_argument('--refresh', type=int, help='Refresh interval in seconds')
    
    # Web dashboard command
    web_parser = subparsers.add_parser('web', help='Start web dashboard')
    web_parser.add_argument('--port', type=int, default=5000, help='Web server port')
    web_parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    # Stock analysis command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze a stock')
    analyze_parser.add_argument('symbol', help='Stock symbol to analyze')
    analyze_parser.add_argument('--trigger', default='manual', help='Analysis trigger')
    
    # Headwind detection command
    headwind_parser = subparsers.add_parser('headwind', help='Run headwind detection')
    headwind_parser.add_argument('symbol', help='Stock symbol')
    headwind_parser.add_argument('drop', type=float, help='Price drop percentage')
    
    # Initialize command
    init_parser = subparsers.add_parser('init', help='Initialize system and create config')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'init':
            # Initialize system
            print("Initializing Mosaic Vault...")
            vault = MosaicVault()
            print("✅ System initialized successfully")
            print("📝 Please configure your .env file with API credentials")
            print("📖 See .env.template for required variables")
            return
        
        # Initialize vault for other commands
        vault = MosaicVault()
        
        if args.command == 'status':
            status = vault.get_status()
            print("=== Mosaic Vault Status ===")
            print(f"Timestamp: {status['timestamp']}")
            print(f"Mock Mode: {status['mock_mode']}")
            print(f"Market Hours: {status['market_hours']}")
            print(f"Agents Initialized: {status['agents_initialized']}")
            print(f"Kite Connected: {status['kite_connected']}")
            
        elif args.command == 'health':
            health = vault.health_check()
            print("=== System Health Check ===")
            print(f"Overall Status: {health['overall_status']}")
            print(f"Portfolio Value: ₹{health.get('portfolio_value', 0):,.2f}")
            print(f"Risk Zone: {health.get('risk_zone', 'UNKNOWN')}")
            print("\\nComponents:")
            for component, status in health['components'].items():
                status_icon = "✅" if "HEALTHY" in str(status) else "⚠️" if "MOCK" in str(status) else "❌"
                print(f"  {status_icon} {component}: {status}")
            
        elif args.command == 'audit':
            audit = vault.run_risk_audit()
            print("=== Risk Audit Results ===")
            print(f"Risk Zone: {audit.get('status', 'UNKNOWN')}")
            print(f"Portfolio Value: ₹{audit.get('total_value', 0):,.2f}")
            print(f"Drawdown: {audit.get('drawdown_pct', 0):.1f}%")
            print(f"Floor Value: ₹{audit.get('floor_value', 0):,.2f}")
            print(f"Cushion: ₹{audit.get('cushion', 0):,.2f}")
            print(f"Recommended Action: {audit.get('action', 'None')}")
            
        elif args.command == 'dashboard':
            vault.start_dashboard(args.refresh)
            
        elif args.command == 'web':
            # Import and start web dashboard
            from simple_web import run_web_dashboard
            run_web_dashboard(port=args.port, debug=args.debug)
            
        elif args.command == 'analyze':
            result = vault.analyze_stock(args.symbol, args.trigger)
            print(f"=== Analysis: {args.symbol} ===")
            print(f"Verdict: {result.get('verdict', 'UNKNOWN')}")
            print(f"Confidence: {result.get('confidence', 0):.1%}")
            print(f"Reasoning: {result.get('reasoning', 'No reasoning provided')}")
            print(f"Timestamp: {result.get('timestamp', 'Unknown')}")
            
        elif args.command == 'headwind':
            result = vault.run_headwind_detection(args.symbol, args.drop)
            print(f"=== Headwind Check: {args.symbol} ===")
            print(f"Price Drop: {args.drop}%")
            print(f"Verdict: {result.get('verdict', 'UNKNOWN')}")
            print(f"Action: {result.get('action', 'UNKNOWN')}")
            print(f"Confidence: {result.get('confidence', 0):.1%}")
            print(f"Reasoning: {result.get('reasoning', 'No reasoning provided')}")
            
    except KeyboardInterrupt:
        print("\\n⏹️  Operation cancelled by user")
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        print(f"❌ Error: {e}")
        if get_config().system.debug_mode:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()