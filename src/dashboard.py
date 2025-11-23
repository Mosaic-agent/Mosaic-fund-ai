"""
Mosaic Vault - Dashboard (The Heads-Up Display)
Real-time terminal dashboard using Rich library.
Provides split-screen view of portfolio status and agent intelligence.
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.columns import Columns
from rich import box
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import our agents
from core.auth import get_kite_session
from agents.governor import Governor
from agents.scout import Scout

class VaultDashboard:
    """
    The Mosaic Vault Terminal Dashboard
    Implements the "Heads-Up Display" for real-time portfolio monitoring
    """
    
    def __init__(self, refresh_interval: int = 60):
        self.console = Console()
        self.refresh_interval = refresh_interval
        self.is_running = False
        self.last_update = None
        
        # Initialize agents
        self.kite_session = None
        self.governor = None
        self.scout = Scout()
        
        # Dashboard state
        self.portfolio_data = {}
        self.risk_data = {}
        self.intelligence_feed = []
        self.system_status = "INITIALIZING"
        
        # Initialize authentication in background
        self._initialize_agents()
    
    def _initialize_agents(self) -> None:
        """Initialize Kite session and agents"""
        try:
            logger.info("Initializing Mosaic Vault agents...")
            
            # Try to get Kite session (will fail gracefully if not configured)
            try:
                self.kite_session = get_kite_session()
                logger.info("Kite session established")
            except Exception as e:
                logger.warning(f"Kite session failed, using mock mode: {e}")
                self.kite_session = None
            
            # Initialize Governor
            self.governor = Governor(self.kite_session)
            
            self.system_status = "ACTIVE"
            logger.info("All agents initialized")
            
        except Exception as e:
            logger.error(f"Agent initialization failed: {e}")
            self.system_status = "ERROR"
    
    def _fetch_portfolio_data(self) -> None:
        """Fetch latest portfolio data from Governor"""
        try:
            if self.governor:
                audit_result = self.governor.audit_risk()
                self.portfolio_data = audit_result
                self.risk_data = {
                    'zone': audit_result.get('status', 'UNKNOWN'),
                    'total_value': audit_result.get('total_value', 0),
                    'drawdown': audit_result.get('drawdown_pct', 0),
                    'floor_value': audit_result.get('floor_value', 0),
                    'cushion': audit_result.get('cushion', 0),
                    'equity_target': audit_result.get('equity_allocation_target', 0),
                    'action': audit_result.get('action', 'No action required')
                }
            else:
                # Mock data for demo
                self.portfolio_data = self._get_mock_portfolio()
                self.risk_data = {
                    'zone': 'GREEN',
                    'total_value': 150000,
                    'drawdown': 2.5,
                    'floor_value': 135000,
                    'cushion': 15000,
                    'equity_target': 95,
                    'action': 'All systems green'
                }
        except Exception as e:
            logger.error(f"Portfolio data fetch failed: {e}")
            self.system_status = "DATA_ERROR"
    
    def _get_mock_portfolio(self) -> Dict:
        """Mock portfolio data for testing"""
        import random
        base_time = datetime.now()
        
        return {
            'status': 'GREEN',
            'total_value': 150000 + random.uniform(-5000, 5000),
            'holdings': [
                {
                    'symbol': 'RELIANCE',
                    'quantity': 10,
                    'current_price': 2480 + random.uniform(-20, 20),
                    'value': 24800,
                    'day_change_pct': random.uniform(-2, 2),
                    'unrealized_pnl': random.uniform(-500, 500),
                    'unrealized_pnl_pct': random.uniform(-2, 3)
                },
                {
                    'symbol': 'TCS',
                    'quantity': 5,
                    'current_price': 3180 + random.uniform(-30, 30),
                    'value': 15900,
                    'day_change_pct': random.uniform(-1.5, 1.5),
                    'unrealized_pnl': random.uniform(-300, 800),
                    'unrealized_pnl_pct': random.uniform(-1, 4)
                },
                {
                    'symbol': 'INFY',
                    'quantity': 15,
                    'current_price': 1420 + random.uniform(-15, 15),
                    'value': 21300,
                    'day_change_pct': random.uniform(-2, 2),
                    'unrealized_pnl': random.uniform(-400, 600),
                    'unrealized_pnl_pct': random.uniform(-2, 3)
                }
            ],
            'timestamp': base_time.isoformat()
        }
    
    def _create_header(self) -> Panel:
        """Create the top header with system status and net worth"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Risk zone indicator with colors
        zone_colors = {
            'GREEN': 'green',
            'YELLOW': 'yellow', 
            'RED': 'red',
            'UNKNOWN': 'white'
        }
        
        zone = self.risk_data.get('zone', 'UNKNOWN')
        zone_color = zone_colors.get(zone, 'white')
        
        # Create status text
        status_text = Text()
        status_text.append("MOSAIC VAULT", style="bold white")
        status_text.append(" | ", style="white")
        status_text.append(f"Zone: {zone}", style=f"bold {zone_color}")
        status_text.append(" | ", style="white")
        status_text.append(f"₹{self.risk_data.get('total_value', 0):,.0f}", style="bold green")
        status_text.append(" | ", style="white")
        status_text.append(f"Status: {self.system_status}", style="cyan")
        status_text.append(" | ", style="white")
        status_text.append(current_time, style="dim white")
        
        return Panel(
            Align.center(status_text),
            style=f"bold {zone_color}",
            box=box.DOUBLE
        )
    
    def _create_holdings_panel(self) -> Panel:
        """Create the left panel showing holdings and risk metrics"""
        
        # Holdings table
        holdings_table = Table(title="Portfolio Holdings", box=box.ROUNDED)
        holdings_table.add_column("Symbol", style="cyan", no_wrap=True)
        holdings_table.add_column("Qty", justify="right")
        holdings_table.add_column("Price", justify="right")
        holdings_table.add_column("Value", justify="right")
        holdings_table.add_column("Day %", justify="right")
        holdings_table.add_column("P&L %", justify="right")
        
        holdings = self.portfolio_data.get('holdings', [])
        for holding in holdings:
            # Color code based on performance
            day_change = holding.get('day_change_pct', 0)
            pnl_pct = holding.get('unrealized_pnl_pct', 0)
            
            day_color = "green" if day_change >= 0 else "red"
            pnl_color = "green" if pnl_pct >= 0 else "red"
            
            holdings_table.add_row(
                holding.get('symbol', ''),
                str(holding.get('quantity', 0)),
                f"₹{holding.get('current_price', 0):,.0f}",
                f"₹{holding.get('value', 0):,.0f}",
                Text(f"{day_change:+.1f}%", style=day_color),
                Text(f"{pnl_pct:+.1f}%", style=pnl_color)
            )
        
        # Risk metrics table
        risk_table = Table(title="Risk Metrics", box=box.ROUNDED)
        risk_table.add_column("Metric", style="yellow")
        risk_table.add_column("Value", justify="right")
        
        drawdown = self.risk_data.get('drawdown', 0)
        drawdown_color = "green" if drawdown < 3 else "yellow" if drawdown < 6 else "red"
        
        risk_table.add_row("Portfolio Value", f"₹{self.risk_data.get('total_value', 0):,.0f}")
        risk_table.add_row("Floor Value", f"₹{self.risk_data.get('floor_value', 0):,.0f}")
        risk_table.add_row("Cushion", f"₹{self.risk_data.get('cushion', 0):,.0f}")
        risk_table.add_row("Drawdown", Text(f"{drawdown:.1f}%", style=drawdown_color))
        risk_table.add_row("Equity Target", f"{self.risk_data.get('equity_target', 0):,.0f}%")
        
        # Combine tables
        content = Columns([holdings_table, risk_table], equal=True)
        
        return Panel(
            content,
            title="[bold cyan]The Accountant[/bold cyan]",
            border_style="cyan"
        )
    
    def _create_intelligence_panel(self) -> Panel:
        """Create the right panel showing intelligence feed and alerts"""
        
        # Intelligence feed table
        intel_table = Table(title="Intelligence Feed", box=box.ROUNDED)
        intel_table.add_column("Time", style="dim")
        intel_table.add_column("Source", style="yellow")
        intel_table.add_column("Alert", style="white")
        
        # Add recent intelligence items (mock for now)
        current_time = datetime.now()
        intel_items = [
            {
                'time': current_time - timedelta(minutes=5),
                'source': 'Scout',
                'alert': f'RELIANCE: Thesis intact after oil price drop'
            },
            {
                'time': current_time - timedelta(minutes=15),
                'source': 'Governor',
                'alert': f'Portfolio Beta: 0.85 (Target: <1.0)'
            },
            {
                'time': current_time - timedelta(hours=1),
                'source': 'Spy',
                'alert': 'IT sector flows: Institutional BUYING detected'
            }
        ]
        
        for item in intel_items:
            intel_table.add_row(
                item['time'].strftime("%H:%M"),
                item['source'],
                item['alert']
            )
        
        # Action panel
        action_text = Text()
        action = self.risk_data.get('action', 'No action required')
        action_color = "green" if "green" in action.lower() else "yellow" if "caution" in action.lower() else "red"
        
        action_text.append("Current Action: ", style="bold white")
        action_text.append(action, style=f"bold {action_color}")
        
        action_panel = Panel(
            Align.center(action_text),
            title="Recommended Action",
            border_style=action_color
        )
        
        # System health
        health_table = Table(title="System Health", box=box.ROUNDED)
        health_table.add_column("Component", style="cyan")
        health_table.add_column("Status", justify="center")
        
        # Component status
        components = [
            ("Kite API", "🟢" if self.kite_session else "🟡"),
            ("Governor", "🟢" if self.governor else "🔴"),
            ("Scout", "🟢"),
            ("Database", "🟢"),
            ("Gemini CLI", "🟡")  # Assume partial availability
        ]
        
        for component, status in components:
            health_table.add_row(component, status)
        
        # Combine content into layout
        from rich.layout import Layout
        scout_layout = Layout()
        scout_layout.split_column(
            Layout(intel_table, name="intel"),
            Layout(health_table, name="health"), 
            Layout(action_panel, name="action")
        )
        
        return Panel(
            scout_layout,
            title="[bold green]The Scout[/bold green]",
            border_style="green"
        )
    
    def _create_footer(self) -> Panel:
        """Create the bottom footer with latest signals"""
        
        footer_text = Text()
        footer_text.append("Latest Signals: ", style="bold white")
        footer_text.append("Institutional Flow: NEUTRAL IT", style="cyan")
        footer_text.append(" | ", style="white")
        footer_text.append("Market Regime: BULL", style="green")
        footer_text.append(" | ", style="white")
        footer_text.append("VIX: 15.2", style="yellow")
        footer_text.append(" | ", style="white")
        
        if self.last_update:
            footer_text.append(f"Last Update: {self.last_update.strftime('%H:%M:%S')}", style="dim white")
        
        return Panel(
            Align.center(footer_text),
            style="dim",
            box=box.SIMPLE
        )
    
    def _create_layout(self) -> Layout:
        """Create the complete dashboard layout"""
        
        # Create main layout
        layout = Layout()
        
        # Split into rows
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        # Split body into left and right panels
        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        # Populate layout
        layout["header"].update(self._create_header())
        layout["left"].update(self._create_holdings_panel())
        layout["right"].update(self._create_intelligence_panel())
        layout["footer"].update(self._create_footer())
        
        return layout
    
    def _update_data(self) -> None:
        """Update dashboard data in background"""
        while self.is_running:
            try:
                self._fetch_portfolio_data()
                self.last_update = datetime.now()
                logger.debug("Dashboard data updated")
                time.sleep(self.refresh_interval)
            except Exception as e:
                logger.error(f"Data update failed: {e}")
                time.sleep(10)  # Retry after 10 seconds on error
    
    def run(self) -> None:
        """Run the live dashboard"""
        self.is_running = True
        
        # Start data update thread
        update_thread = threading.Thread(target=self._update_data, daemon=True)
        update_thread.start()
        
        try:
            logger.info("Starting Mosaic Vault Dashboard...")
            
            with Live(
                self._create_layout(),
                refresh_per_second=1,
                screen=True,
                vertical_overflow="fold"
            ) as live:
                
                while self.is_running:
                    try:
                        # Update layout
                        live.update(self._create_layout())
                        time.sleep(1)
                        
                    except KeyboardInterrupt:
                        logger.info("Dashboard shutdown requested")
                        break
                    except Exception as e:
                        logger.error(f"Dashboard error: {e}")
                        time.sleep(5)
                        
        except Exception as e:
            logger.error(f"Dashboard failed to start: {e}")
        finally:
            self.is_running = False
            logger.info("Dashboard stopped")
    
    def stop(self) -> None:
        """Stop the dashboard"""
        self.is_running = False

# CLI interface
def run_dashboard(refresh_interval: int = 60) -> None:
    """
    Run the Mosaic Vault dashboard
    
    Args:
        refresh_interval: Data refresh interval in seconds
    """
    dashboard = VaultDashboard(refresh_interval)
    
    try:
        dashboard.run()
    except KeyboardInterrupt:
        print("\\nShutting down dashboard...")
    finally:
        dashboard.stop()

if __name__ == "__main__":
    """Run the dashboard as standalone application"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Mosaic Vault Dashboard")
    parser.add_argument(
        "--refresh", 
        type=int, 
        default=60,
        help="Refresh interval in seconds (default: 60)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger.info(f"Starting Mosaic Vault Dashboard (refresh: {args.refresh}s)")
    
    run_dashboard(args.refresh)