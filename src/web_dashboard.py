"""
Mosaic Vault - Web Dashboard
Flask-based web interface with real-time updates.
"""

from flask import Flask, render_template, jsonify, request
import threading
import time
import json
from datetime import datetime
import os
import sys
import logging
from typing import Dict, List, Optional

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__)))

from core.auth import get_kite_session
from agents.governor import Governor
from agents.scout import Scout

# Configure logger
logger = logging.getLogger(__name__)
from agents.scout import Scout
from config import get_config

# Configure logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)

class WebDashboard:
    """
    Web-based Mosaic Vault dashboard
    """
    
    def __init__(self, port=5000, debug=False):
        self.app = Flask(__name__, template_folder='templates', static_folder='static')
        self.app.config['SECRET_KEY'] = 'mosaic-vault-secret-key'
        
        # Initialize system components
        self.config = get_config()
        self.kite_session = None
        self.governor = None
        self.scout = Scout()
        self.port = port
        self.debug = debug
        
        # Dashboard state
        self.portfolio_data = {}
        self.is_running = False
        
        # Setup routes
        self._setup_routes()
        self._initialize_system()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            return render_template('dashboard.html')
        
        @self.app.route('/api/status')
        def api_status():
            return jsonify({
                'timestamp': datetime.now().isoformat(),
                'status': 'active',
                'mock_mode': self.config.system.mock_mode,
                'market_hours': self.config.is_market_hours(),
                'kite_connected': bool(self.kite_session)
            })
        
        @self.app.route('/api/portfolio')
        def api_portfolio():
            if self.governor:
                try:
                    # Get detailed portfolio data
                    portfolio_value, holdings = self.governor.get_current_portfolio()
                    status = self.governor.get_portfolio_status()
                    
                    # Calculate additional metrics
                    total_investment = sum(h.quantity * h.avg_price for h in holdings) if holdings else 0
                    total_pnl = portfolio_value - total_investment
                    total_pnl_pct = (total_pnl / total_investment) * 100 if total_investment > 0 else 0
                    
                    # Day's performance
                    day_pnl = sum(h.day_change * h.quantity for h in holdings) if holdings else 0
                    day_pnl_pct = (day_pnl / portfolio_value) * 100 if portfolio_value > 0 else 0
                    
                    # Performance categorization
                    gainers = [h for h in holdings if h.unrealized_pnl > 0] if holdings else []
                    losers = [h for h in holdings if h.unrealized_pnl < 0] if holdings else []
                    
                    # Top performers
                    top_gainer = max(gainers, key=lambda x: x.unrealized_pnl_pct) if gainers else None
                    top_loser = min(losers, key=lambda x: x.unrealized_pnl_pct) if losers else None
                    
                    return jsonify({
                        'portfolio_value': round(portfolio_value, 2),
                        'total_investment': round(total_investment, 2),
                        'total_pnl': round(total_pnl, 2),
                        'total_pnl_pct': round(total_pnl_pct, 2),
                        'day_pnl': round(day_pnl, 2),
                        'day_pnl_pct': round(day_pnl_pct, 2),
                        'holdings_count': len(holdings) if holdings else 0,
                        'gainers_count': len(gainers),
                        'losers_count': len(losers),
                        'risk_zone': status.get('risk_zone', 'Unknown'),
                        'floor_protection': status.get('floor_protection', False),
                        'top_gainer': {
                            'symbol': top_gainer.symbol,
                            'pnl_pct': round(top_gainer.unrealized_pnl_pct, 2),
                            'pnl': round(top_gainer.unrealized_pnl, 2)
                        } if top_gainer else None,
                        'top_loser': {
                            'symbol': top_loser.symbol,
                            'pnl_pct': round(top_loser.unrealized_pnl_pct, 2),
                            'pnl': round(top_loser.unrealized_pnl, 2)
                        } if top_loser else None,
                        'holdings': [
                            {
                                'symbol': h.symbol,
                                'quantity': h.quantity,
                                'avg_price': round(h.avg_price, 2),
                                'current_price': round(h.current_price, 2),
                                'value': round(h.value, 2),
                                'day_change': round(h.day_change, 2),
                                'day_change_pct': round(h.day_change_pct, 2),
                                'unrealized_pnl': round(h.unrealized_pnl, 2),
                                'unrealized_pnl_pct': round(h.unrealized_pnl_pct, 2)
                            } for h in holdings
                        ] if holdings else [],
                        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    
                except Exception as e:
                    logger.error(f"Error in portfolio API: {e}")
                    return jsonify({'error': f'Portfolio fetch failed: {str(e)}'}), 500
            return jsonify({'error': 'Governor not initialized'})
        
        @self.app.route('/api/analyze/<symbol>')
        def api_analyze(symbol):
            try:
                result = self.scout.analyze_ticker(symbol.upper(), 'web_request')
                return jsonify({
                    'symbol': result.symbol,
                    'verdict': result.verdict.value,
                    'confidence': result.confidence,
                    'reasoning': result.reasoning,
                    'timestamp': result.timestamp.isoformat()
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/headwind/<symbol>/<float:drop>')
        def api_headwind(symbol, drop):
            try:
                result = self.scout.run_headwind_check(symbol.upper(), drop)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
    
    def _setup_socketio_events(self):
        """Setup WebSocket events"""
        
        @self.socketio.on('connect')
        def handle_connect():
            print(f"Client connected: {request.sid}")
            # Send initial data
            if self.governor:
                portfolio_data = self.governor.audit_risk()
                emit('portfolio_update', portfolio_data)
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            print(f"Client disconnected: {request.sid}")
        
        @self.socketio.on('request_analysis')
        def handle_analysis_request(data):
            symbol = data.get('symbol', '').upper()
            if symbol:
                try:
                    result = self.scout.analyze_ticker(symbol, 'websocket_request')
                    emit('analysis_result', {
                        'symbol': result.symbol,
                        'verdict': result.verdict.value,
                        'confidence': result.confidence,
                        'reasoning': result.reasoning,
                        'timestamp': result.timestamp.isoformat()
                    })
                except Exception as e:
                    emit('analysis_error', {'error': str(e)})
    
    def _initialize_system(self):
        """Initialize system components"""
        try:
            print("🔧 Initializing Mosaic Vault web system...")
            
            # Try to get Kite session
            if not self.config.system.mock_mode:
                try:
                    self.kite_session = get_kite_session()
                    print("✅ Kite session established")
                except Exception as e:
                    print(f"⚠️ Kite authentication failed, using mock mode: {e}")
                    self.config.system.mock_mode = True
            
            # Initialize Governor
            self.governor = Governor(self.kite_session)
            print("✅ System initialized successfully")
            
        except Exception as e:
            print(f"❌ System initialization failed: {e}")
    
    def _update_data_loop(self):
        """Background thread for real-time data updates"""
        while self.is_running:
            try:
                if self.governor:
                    # Get portfolio update
                    portfolio_data = self.governor.audit_risk()
                    
                    # Emit to all connected clients
                    self.socketio.emit('portfolio_update', portfolio_data)
                    
                    # Check for risk zone changes
                    current_zone = portfolio_data.get('status', 'UNKNOWN')
                    if hasattr(self, 'last_zone') and self.last_zone != current_zone:
                        self.socketio.emit('zone_change', {
                            'old_zone': self.last_zone,
                            'new_zone': current_zone,
                            'portfolio_value': portfolio_data.get('total_value', 0),
                            'timestamp': datetime.now().isoformat()
                        })
                    
                    self.last_zone = current_zone
                
                # Sleep for update interval
                time.sleep(10)  # Update every 10 seconds for web
                
            except Exception as e:
                print(f"❌ Data update error: {e}")
                time.sleep(30)  # Wait longer on error
    
    def run(self):
        """Start the web dashboard"""
        print(f"🚀 Starting Mosaic Vault Web Dashboard on http://localhost:{self.port}")
        
        # Start background update thread
        self.is_running = True
        self.update_thread = threading.Thread(target=self._update_data_loop, daemon=True)
        self.update_thread.start()
        
        # Create templates directory if it doesn't exist
        os.makedirs(os.path.join(os.path.dirname(__file__), 'templates'), exist_ok=True)
        os.makedirs(os.path.join(os.path.dirname(__file__), 'static'), exist_ok=True)
        
        try:
            # Run Flask app with SocketIO
            self.socketio.run(
                self.app,
                host='0.0.0.0',
                port=self.port,
                debug=self.debug,
                allow_unsafe_werkzeug=True
            )
        except KeyboardInterrupt:
            print("\\n🛑 Shutting down web dashboard...")
        finally:
            self.is_running = False

if __name__ == "__main__":
    dashboard = WebDashboard(port=5000, debug=True)
    dashboard.run()