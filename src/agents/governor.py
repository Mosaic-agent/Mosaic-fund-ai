"""
Mosaic Vault - The Governor (Risk Engine)
Implements CPPI model with strict -10% floor enforcement.
Manages the traffic light system and portfolio allocation.
"""

import sqlite3
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import yfinance as yf
import pandas as pd

# Setup logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

class RiskZone(Enum):
    """Risk zone classification for traffic light system"""
    GREEN = "GREEN"    # 0% to -5% drawdown
    YELLOW = "YELLOW"  # -5% to -8% drawdown  
    RED = "RED"        # >-8% drawdown

@dataclass
class PortfolioState:
    """Portfolio state snapshot"""
    total_value: float
    peak_value: float
    drawdown_pct: float
    risk_zone: RiskZone
    equity_allocation: float
    liquid_allocation: float
    recommended_action: str
    timestamp: datetime

@dataclass
class Holding:
    """Individual stock holding"""
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    value: float
    day_change: float
    day_change_pct: float
    unrealized_pnl: float
    unrealized_pnl_pct: float

class CPPIEngine:
    """
    Constant Proportion Portfolio Insurance Engine
    Implements mathematical floor protection with dynamic allocation
    """
    
    def __init__(self, db_path: str = "data/vault.db"):
        self.db_path = db_path
        self.floor_ratio = 0.9  # 90% of all-time high
        self.multipliers = {
            RiskZone.GREEN: 5.0,   # Aggressive
            RiskZone.YELLOW: 3.0,  # Defensive
            RiskZone.RED: 1.0      # Conservative
        }
        self._initialize_database()
    
    def _initialize_database(self) -> None:
        """Initialize SQLite database with required tables"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS portfolio_state (
                    timestamp DATETIME PRIMARY KEY,
                    total_value REAL,
                    peak_value REAL,
                    drawdown_pct REAL,
                    risk_zone TEXT,
                    equity_allocation REAL,
                    liquid_allocation REAL,
                    action_taken TEXT
                );
                
                CREATE TABLE IF NOT EXISTS holdings_history (
                    timestamp DATETIME,
                    symbol TEXT,
                    quantity INTEGER,
                    avg_price REAL,
                    current_price REAL,
                    value REAL,
                    PRIMARY KEY (timestamp, symbol)
                );
                
                CREATE TABLE IF NOT EXISTS risk_events (
                    timestamp DATETIME PRIMARY KEY,
                    event_type TEXT,
                    portfolio_value REAL,
                    drawdown_pct REAL,
                    action_taken TEXT,
                    details TEXT
                );
                
                CREATE TABLE IF NOT EXISTS peak_tracker (
                    id INTEGER PRIMARY KEY,
                    peak_value REAL,
                    peak_date DATETIME,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Initialize peak value if not exists
            cursor = conn.execute("SELECT COUNT(*) FROM peak_tracker")
            if cursor.fetchone()[0] == 0:
                conn.execute(
                    "INSERT INTO peak_tracker (peak_value, peak_date) VALUES (?, ?)",
                    (100000.0, datetime.now())  # Default starting value
                )
    
    def _get_peak_value(self) -> float:
        """Get the all-time high portfolio value"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT peak_value FROM peak_tracker ORDER BY id DESC LIMIT 1"
            )
            result = cursor.fetchone()
            return result[0] if result else 100000.0
    
    def _update_peak_value(self, new_value: float) -> None:
        """Update peak value if new high achieved"""
        current_peak = self._get_peak_value()
        
        if new_value > current_peak:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE peak_tracker SET peak_value = ?, peak_date = ?, updated_at = ? WHERE id = (SELECT MAX(id) FROM peak_tracker)",
                    (new_value, datetime.now(), datetime.now())
                )
            logger.info(f"New portfolio peak achieved: ₹{new_value:,.2f}")
    
    def _calculate_drawdown(self, current_value: float, peak_value: float) -> float:
        """Calculate portfolio drawdown percentage"""
        if peak_value == 0:
            return 0.0
        return (peak_value - current_value) / peak_value
    
    def _determine_risk_zone(self, drawdown_pct: float) -> RiskZone:
        """Determine risk zone based on drawdown percentage"""
        if drawdown_pct <= 0.05:  # 0% to -5%
            return RiskZone.GREEN
        elif drawdown_pct <= 0.08:  # -5% to -8%
            return RiskZone.YELLOW
        else:  # >-8%
            return RiskZone.RED
    
    def _calculate_cppi_allocation(self, current_value: float, peak_value: float, risk_zone: RiskZone) -> Tuple[float, float]:
        """
        Calculate CPPI-based asset allocation
        
        Returns:
            Tuple[float, float]: (equity_allocation_pct, liquid_allocation_pct)
        """
        floor = self.floor_ratio * peak_value
        cushion = max(0, current_value - floor)
        multiplier = self.multipliers[risk_zone]
        
        # Calculate equity allocation as percentage of portfolio
        if current_value > 0:
            equity_allocation = min(1.0, (cushion * multiplier) / current_value)
        else:
            equity_allocation = 0.0
        
        liquid_allocation = 1.0 - equity_allocation
        
        logger.debug(f"CPPI Calculation: Floor=₹{floor:,.2f}, Cushion=₹{cushion:,.2f}, "
                    f"Multiplier={multiplier}, Equity%={equity_allocation:.1%}")
        
        return equity_allocation, liquid_allocation
    
    def _get_recommended_action(self, risk_zone: RiskZone, equity_allocation: float) -> str:
        """Generate recommended action based on risk zone and allocation"""
        if risk_zone == RiskZone.RED:
            if equity_allocation < 0.3:
                return "EMERGENCY: Liquidate to Liquid BeES immediately"
            else:
                return "RED ZONE: Reduce equity exposure to match CPPI allocation"
        elif risk_zone == RiskZone.YELLOW:
            return "CAUTION: Trim high-beta positions, move to arbitrage funds"
        else:  # GREEN
            return "ALL CLEAR: Full equity allocation permitted"
    
    def _save_portfolio_state(self, state: PortfolioState) -> None:
        """Save portfolio state to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO portfolio_state 
                (timestamp, total_value, peak_value, drawdown_pct, risk_zone, 
                 equity_allocation, liquid_allocation, action_taken)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                state.timestamp,
                state.total_value,
                state.peak_value,
                state.drawdown_pct,
                state.risk_zone.value,
                state.equity_allocation,
                state.liquid_allocation,
                state.recommended_action
            ))
    
    def _log_risk_event(self, event_type: str, portfolio_value: float, 
                       drawdown_pct: float, action_taken: str, details: str = "") -> None:
        """Log significant risk events"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO risk_events 
                (timestamp, event_type, portfolio_value, drawdown_pct, action_taken, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (datetime.now(), event_type, portfolio_value, drawdown_pct, action_taken, details))

class Governor:
    """
    The Governor - Master Risk Controller
    Orchestrates portfolio risk management and CPPI enforcement
    """
    
    def __init__(self, kite_session=None):
        self.kite = kite_session
        self.cppi = CPPIEngine()
        self.last_audit_time = None
        # Store credentials for creating temp sessions
        self.api_key = None
        self.api_secret = None
    
    def set_credentials(self, api_key: str, api_secret: str):
        """Set API credentials for creating temporary Kite sessions"""
        self.api_key = api_key
        self.api_secret = api_secret
        
    def fetch_live_holdings(self, access_token=None) -> List[Holding]:
        """
        Fetch live holdings from Zerodha with enhanced error handling and data validation
        """
        kite_session = self.kite
        
        # If access token provided, create temporary session
        if access_token and self.api_key:
            try:
                from kiteconnect import KiteConnect
                kite_session = KiteConnect(api_key=self.api_key)
                kite_session.set_access_token(access_token)
                logger.info("Using provided access token for holdings fetch")
            except Exception as e:
                logger.error(f"Failed to create temp Kite session: {e}")
                kite_session = self.kite
        
        if not kite_session:
            logger.warning("No Kite session available, using mock data")
            return self._get_mock_holdings()
        
        try:
            logger.info("Fetching live holdings from Zerodha...")
            
            # Get holdings and positions from Zerodha
            holdings_data = kite_session.holdings()
            logger.info(f"Retrieved {len(holdings_data)} holdings from Kite")
            
            # Get positions for today's trades
            positions_data = kite_session.positions()
            net_positions = positions_data.get('net', [])
            logger.info(f"Retrieved {len(net_positions)} positions from Kite")
            
            holdings = []
            
            # Process long-term holdings
            for holding in holdings_data:
                try:
                    symbol = holding['tradingsymbol']
                    quantity = int(holding['quantity'])
                    
                    # Skip if no quantity
                    if quantity <= 0:
                        continue
                    
                    avg_price = float(holding['average_price'])
                    last_price = float(holding.get('last_price', 0))
                    
                    # If last_price is 0, fetch from yfinance
                    if last_price <= 0:
                        current_price = self._get_current_price(symbol)
                    else:
                        current_price = last_price
                    
                    if current_price > 0:
                        value = quantity * current_price
                        prev_close = float(holding.get('close_price', current_price))
                        
                        day_change = current_price - prev_close
                        day_change_pct = (day_change / prev_close) * 100 if prev_close > 0 else 0
                        
                        unrealized_pnl = (current_price - avg_price) * quantity
                        unrealized_pnl_pct = ((current_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
                        
                        holdings.append(Holding(
                            symbol=symbol,
                            quantity=quantity,
                            avg_price=avg_price,
                            current_price=current_price,
                            value=value,
                            day_change=day_change,
                            day_change_pct=day_change_pct,
                            unrealized_pnl=unrealized_pnl,
                            unrealized_pnl_pct=unrealized_pnl_pct
                        ))
                        
                        logger.debug(f"Processed holding: {symbol} - Qty: {quantity}, Price: ₹{current_price:.2f}")
                    
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Error processing holding {holding.get('tradingsymbol', 'Unknown')}: {e}")
                    continue
            
            # Process day positions (if any significant ones)
            for position in net_positions:
                try:
                    symbol = position['tradingsymbol']
                    quantity = int(position['quantity'])
                    
                    # Skip if no position or already in holdings
                    if quantity == 0 or any(h.symbol == symbol for h in holdings):
                        continue
                    
                    avg_price = float(position['average_price'])
                    last_price = float(position.get('last_price', 0))
                    
                    if last_price <= 0:
                        current_price = self._get_current_price(symbol)
                    else:
                        current_price = last_price
                    
                    if current_price > 0 and abs(quantity * current_price) > 1000:  # Only significant positions
                        value = quantity * current_price
                        day_change = float(position.get('day_change', 0))
                        day_change_pct = float(position.get('day_change_percentage', 0))
                        
                        pnl = float(position.get('pnl', 0))
                        pnl_pct = (pnl / abs(avg_price * quantity)) * 100 if avg_price > 0 else 0
                        
                        holdings.append(Holding(
                            symbol=f"{symbol}*",  # Mark as position
                            quantity=quantity,
                            avg_price=avg_price,
                            current_price=current_price,
                            value=value,
                            day_change=day_change,
                            day_change_pct=day_change_pct,
                            unrealized_pnl=pnl,
                            unrealized_pnl_pct=pnl_pct
                        ))
                        
                        logger.debug(f"Processed position: {symbol} - Qty: {quantity}, P&L: ₹{pnl:.2f}")
                
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Error processing position {position.get('tradingsymbol', 'Unknown')}: {e}")
                    continue
            
            logger.info(f"Successfully processed {len(holdings)} holdings/positions")
            return holdings
            
        except Exception as e:
            logger.error(f"Failed to fetch holdings from Kite: {e}")
            logger.info("Falling back to mock data")
            return self._get_mock_holdings()
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current price from yfinance (free data source)"""
        try:
            # Convert NSE symbol to Yahoo format if needed
            yahoo_symbol = f"{symbol}.NS" if not symbol.endswith('.NS') else symbol
            
            ticker = yf.Ticker(yahoo_symbol)
            data = ticker.history(period="1d", interval="1m")
            
            if not data.empty:
                return float(data['Close'].iloc[-1])
            else:
                logger.warning(f"No price data for {symbol}")
                return 0.0
                
        except Exception as e:
            logger.warning(f"Price fetch failed for {symbol}: {e}")
            return 0.0
    
    def _get_mock_holdings(self) -> List[Holding]:
        """Mock holdings for testing without Kite connection"""
        return [
            Holding("RELIANCE", 10, 2500.0, 2480.0, 24800.0, -20.0, -0.8, -200.0, -0.8),
            Holding("TCS", 5, 3200.0, 3180.0, 15900.0, -20.0, -0.6, -100.0, -0.6),
            Holding("INFY", 15, 1400.0, 1420.0, 21300.0, 20.0, 1.4, 300.0, 2.1),
        ]
    
    def audit_risk(self, access_token=None) -> Dict:
        """
        Main risk audit function - The Governor's core responsibility
        
        Returns:
            Dict: Complete risk assessment and recommendations
        """
        try:
            # Fetch current holdings
            holdings = self.fetch_live_holdings(access_token)
            
            # Calculate total portfolio value
            total_value = sum(holding.value for holding in holdings)
            
            # Get peak value and update if necessary
            peak_value = self.cppi._get_peak_value()
            self.cppi._update_peak_value(total_value)
            peak_value = max(peak_value, total_value)  # Use updated peak
            
            # Calculate drawdown
            drawdown_pct = self.cppi._calculate_drawdown(total_value, peak_value)
            
            # Determine risk zone
            risk_zone = self.cppi._determine_risk_zone(drawdown_pct)
            
            # Calculate CPPI allocation
            equity_allocation, liquid_allocation = self.cppi._calculate_cppi_allocation(
                total_value, peak_value, risk_zone
            )
            
            # Get recommended action
            recommended_action = self.cppi._get_recommended_action(risk_zone, equity_allocation)
            
            # Create portfolio state
            state = PortfolioState(
                total_value=total_value,
                peak_value=peak_value,
                drawdown_pct=drawdown_pct,
                risk_zone=risk_zone,
                equity_allocation=equity_allocation,
                liquid_allocation=liquid_allocation,
                recommended_action=recommended_action,
                timestamp=datetime.now()
            )
            
            # Save state to database
            self.cppi._save_portfolio_state(state)
            
            # Log risk events if zone changed
            self._check_zone_changes(state)
            
            # Create response dictionary
            response = {
                'status': risk_zone.value,
                'total_value': total_value,
                'peak_value': peak_value,
                'drawdown_pct': drawdown_pct * 100,  # Convert to percentage
                'floor_value': peak_value * self.cppi.floor_ratio,
                'cushion': max(0, total_value - (peak_value * self.cppi.floor_ratio)),
                'equity_allocation_target': equity_allocation * 100,
                'liquid_allocation_target': liquid_allocation * 100,
                'action': recommended_action,
                'holdings': [
                    {
                        'symbol': h.symbol,
                        'quantity': h.quantity,
                        'current_price': h.current_price,
                        'value': h.value,
                        'day_change_pct': h.day_change_pct,
                        'unrealized_pnl': h.unrealized_pnl,
                        'unrealized_pnl_pct': h.unrealized_pnl_pct
                    }
                    for h in holdings
                ],
                'timestamp': state.timestamp.isoformat()
            }
            
            logger.info(f"Risk Audit Complete - Zone: {risk_zone.value}, "
                       f"Value: ₹{total_value:,.2f}, Drawdown: {drawdown_pct:.1%}")
            
            self.last_audit_time = datetime.now()
            return response
            
        except Exception as e:
            logger.error(f"Risk audit failed: {e}")
            return {
                'status': 'ERROR',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _check_zone_changes(self, state: PortfolioState) -> None:
        """Check for risk zone changes and log events"""
        # Get previous state from database
        with sqlite3.connect(self.cppi.db_path) as conn:
            cursor = conn.execute("""
                SELECT risk_zone FROM portfolio_state 
                ORDER BY timestamp DESC LIMIT 1 OFFSET 1
            """)
            result = cursor.fetchone()
            
            if result:
                prev_zone = result[0]
                if prev_zone != state.risk_zone.value:
                    self.cppi._log_risk_event(
                        event_type="ZONE_CHANGE",
                        portfolio_value=state.total_value,
                        drawdown_pct=state.drawdown_pct,
                        action_taken=state.recommended_action,
                        details=f"Zone changed from {prev_zone} to {state.risk_zone.value}"
                    )
                    logger.warning(f"Risk zone changed: {prev_zone} → {state.risk_zone.value}")
    
    def get_portfolio_beta(self) -> float:
        """
        Calculate portfolio beta against NIFTY 50
        Uses yfinance for free historical data
        """
        try:
            holdings = self.fetch_live_holdings()
            total_value = sum(h.value for h in holdings)
            
            if total_value == 0:
                return 0.0
            
            portfolio_beta = 0.0
            nifty_data = yf.Ticker("^NSEI").history(period="1y")['Close']
            
            for holding in holdings:
                weight = holding.value / total_value
                stock_data = yf.Ticker(f"{holding.symbol}.NS").history(period="1y")['Close']
                
                if len(stock_data) > 50 and len(nifty_data) > 50:
                    # Align data
                    combined_data = pd.DataFrame({
                        'stock': stock_data,
                        'nifty': nifty_data
                    }).dropna()
                    
                    if len(combined_data) > 30:
                        # Calculate beta
                        stock_returns = combined_data['stock'].pct_change().dropna()
                        nifty_returns = combined_data['nifty'].pct_change().dropna()
                        
                        covariance = stock_returns.cov(nifty_returns)
                        nifty_variance = nifty_returns.var()
                        
                        if nifty_variance > 0:
                            stock_beta = covariance / nifty_variance
                            portfolio_beta += weight * stock_beta
            
            logger.debug(f"Portfolio Beta: {portfolio_beta:.2f}")
            return portfolio_beta
            
        except Exception as e:
            logger.error(f"Beta calculation failed: {e}")
            return 1.0  # Default to market beta
    
    def get_health_summary(self) -> Dict:
        """Get a quick health summary of the vault"""
        try:
            audit_result = self.audit_risk()
            portfolio_beta = self.get_portfolio_beta()
            
            return {
                'vault_health': audit_result['status'],
                'portfolio_value': audit_result.get('total_value', 0),
                'drawdown': audit_result.get('drawdown_pct', 0),
                'portfolio_beta': portfolio_beta,
                'last_audit': self.last_audit_time.isoformat() if self.last_audit_time else None,
                'emergency_action_required': audit_result['status'] == 'RED'
            }
            
        except Exception as e:
            logger.error(f"Health summary failed: {e}")
            return {'vault_health': 'ERROR', 'error': str(e)}

# Convenience functions
def audit_risk(kite_session=None) -> Dict:
    """Convenience function for direct risk audit"""
    governor = Governor(kite_session)
    return governor.audit_risk()

def get_vault_health(kite_session=None) -> Dict:
    """Quick vault health check"""
    governor = Governor(kite_session)
    return governor.get_health_summary()

if __name__ == "__main__":
    """Test the governor module"""
    # Test without Kite session (uses mock data)
    logger.info("Testing Governor with mock data...")
    result = audit_risk()
    print(f"Risk Audit Result: {result['status']}")
    print(f"Portfolio Value: ₹{result.get('total_value', 0):,.2f}")
    print(f"Recommended Action: {result.get('action', 'Unknown')}")