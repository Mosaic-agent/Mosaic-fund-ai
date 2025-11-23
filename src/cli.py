import argparse
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class CLI:
    def __init__(self):
        self.parser = self._setup_argument_parser()
        
    def _setup_argument_parser(self):
        """Sets up the argument parser for the CLI."""
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
        
        return parser

    def run(self, args: Optional[List[str]] = None):
        """Parses arguments and dispatches commands."""
        parsed_args = self.parser.parse_args(args)
        
        if not parsed_args.command:
            self.parser.print_help()
            return
        
        # This will be replaced with actual command dispatch logic
        logger.info(f"Command '{parsed_args.command}' called with args: {parsed_args}")
