"""
Mosaic Vault - Simple Web Dashboard
Flask-based web interface for portfolio monitoring.
"""

from flask import Flask, render_template, jsonify, request, make_response
import threading
import time
import json
from datetime import datetime, timedelta
import os
import sys
import logging
from typing import Dict, List, Optional

# Add src to path for imports
sys.path.append(os.path.dirname(__file__))

from core.auth import get_kite_session
from agents.governor import Governor
from agents.scout import Scout
from config import get_config

# Configure logger
logger = logging.getLogger(__name__)

class WebDashboard:
    """
    Simple web-based dashboard for Mosaic Vault
    """
    
    def __init__(self, port: int = 5000, debug: bool = False):
        self.app = Flask(__name__)
        self.port = port
        self.debug = debug
        
        # Initialize system components
        self.config = get_config()
        self.kite_session = None
        self.governor = None
        self.scout = Scout()
        
        # Setup routes
        self._setup_routes()
        self._initialize_system()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            """Main dashboard page"""
            return '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Mosaic Vault - Dashboard</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { 
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                        margin: 0; 
                        padding: 20px; 
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                    }
                    .container { 
                        max-width: 1200px; 
                        margin: 0 auto; 
                        background: white; 
                        border-radius: 10px; 
                        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                        overflow: hidden;
                    }
                    .header { 
                        background: linear-gradient(45deg, #2c3e50, #34495e); 
                        color: white; 
                        padding: 20px; 
                        text-align: center; 
                    }
                    .header h1 { margin: 0; font-size: 2.5em; }
                    .header p { margin: 10px 0 0 0; opacity: 0.8; }
                    .dashboard { 
                        display: grid; 
                        grid-template-columns: 1fr 1fr; 
                        gap: 20px; 
                        padding: 20px; 
                    }
                    .panel { 
                        background: #f8f9fa; 
                        border-radius: 8px; 
                        padding: 20px; 
                        border-left: 4px solid #3498db;
                    }
                    .panel h3 { margin-top: 0; color: #2c3e50; }
                    .risk-zone { 
                        display: inline-block; 
                        padding: 8px 16px; 
                        border-radius: 20px; 
                        font-weight: bold; 
                        text-transform: uppercase;
                    }
                    .risk-green { background: #2ecc71; color: white; }
                    .risk-yellow { background: #f39c12; color: white; }
                    .risk-red { background: #e74c3c; color: white; }
                    .metric { 
                        display: flex; 
                        justify-content: space-between; 
                        margin: 10px 0; 
                        padding: 10px; 
                        background: white; 
                        border-radius: 4px;
                    }
                    .metric-value { font-weight: bold; }
                    .holdings-table { 
                        width: 100%; 
                        border-collapse: collapse; 
                        margin-top: 15px;
                    }
                    .holdings-table th, .holdings-table td { 
                        padding: 12px; 
                        text-align: left; 
                        border-bottom: 1px solid #ddd; 
                    }
                    .holdings-table th { 
                        background: #34495e; 
                        color: white; 
                    }
                    .positive { color: #27ae60; }
                    .negative { color: #e74c3c; }
                    .refresh-btn { 
                        background: #3498db; 
                        color: white; 
                        border: none; 
                        padding: 10px 20px; 
                        border-radius: 4px; 
                        cursor: pointer; 
                        margin: 10px 5px;
                    }
                    .refresh-btn:hover { background: #2980b9; }
                    .analysis-section { 
                        grid-column: 1 / -1; 
                        margin-top: 20px; 
                    }
                    .analysis-input { 
                        padding: 10px; 
                        border: 1px solid #ddd; 
                        border-radius: 4px; 
                        margin: 5px;
                    }
                    .footer { 
                        text-align: center; 
                        padding: 20px; 
                        background: #f8f9fa; 
                        color: #666; 
                        border-top: 1px solid #ddd;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🏛️ MOSAIC VAULT</h1>
                        <p id="header-subtitle">Autonomous Family Office System</p>
                        <div id="user-profile" style="margin-top: 10px; font-size: 0.9em; opacity: 0.8;"></div>
                    </div>
                    
                    <div class="dashboard">
                        <div class="panel">
                            <h3>📊 Portfolio Status</h3>
                            <div id="portfolio-status">Loading...</div>
                        </div>
                        
                        <div class="panel">
                            <h3>🛡️ Risk Management</h3>
                            <div id="risk-status">Loading...</div>
                        </div>
                        
                        <div class="panel">
                            <h3>💼 Holdings</h3>
                            <div id="holdings-data">Loading...</div>
                        </div>
                        
                        <div class="panel">
                            <h3>🔍 Analysis</h3>
                            <input type="text" id="symbol-input" class="analysis-input" placeholder="Enter symbol (e.g., RELIANCE)" />
                            <button class="refresh-btn" onclick="analyzeStock()">Analyze</button>
                            <div id="analysis-result"></div>
                        </div>
                        
                        <div class="panel" id="auth-panel">
                            <h3>🔐 Authentication</h3>
                            <div id="auth-status">Checking...</div>
                            <div id="auth-details" style="margin-top: 10px; font-size: 0.9em; color: #666;"></div>
                            <button class="refresh-btn" id="login-btn" onclick="authenticateKite()" style="display:none;">🔑 Connect to Kite</button>
                            <button class="refresh-btn" id="logout-btn" onclick="clearAuthCookies()" style="display:none; background: #e74c3c;">🚪 Logout</button>
                        </div>
                    </div>
                    
                    <div class="footer">
                        <p>Last updated: <span id="last-update">Never</span></p>
                        <button class="refresh-btn" onclick="refreshData()">🔄 Refresh All</button>
                    </div>
                </div>
                
                <script>
                    function updatePortfolioStatus(data) {
                        const statusDiv = document.getElementById('portfolio-status');
                        const riskClass = data.status.toLowerCase() === 'green' ? 'risk-green' : 
                                         data.status.toLowerCase() === 'yellow' ? 'risk-yellow' : 'risk-red';
                        
                        statusDiv.innerHTML = `
                            <div class="metric">
                                <span>Portfolio Value:</span>
                                <span class="metric-value">₹${data.total_value.toLocaleString()}</span>
                            </div>
                            <div class="metric">
                                <span>Risk Zone:</span>
                                <span class="risk-zone ${riskClass}">${data.status}</span>
                            </div>
                            <div class="metric">
                                <span>Drawdown:</span>
                                <span class="metric-value ${data.drawdown_pct > 5 ? 'negative' : 'positive'}">${data.drawdown_pct.toFixed(1)}%</span>
                            </div>
                            <div class="metric">
                                <span>Action:</span>
                                <span class="metric-value">${data.action}</span>
                            </div>
                        `;
                    }
                    
                    function updateRiskStatus(data) {
                        const riskDiv = document.getElementById('risk-status');
                        riskDiv.innerHTML = `
                            <div class="metric">
                                <span>Floor Value:</span>
                                <span class="metric-value">₹${data.floor_value.toLocaleString()}</span>
                            </div>
                            <div class="metric">
                                <span>Cushion:</span>
                                <span class="metric-value">₹${data.cushion.toLocaleString()}</span>
                            </div>
                            <div class="metric">
                                <span>Equity Target:</span>
                                <span class="metric-value">${data.equity_allocation_target.toFixed(0)}%</span>
                            </div>
                        `;
                    }
                    
                    function updateHoldings(holdings) {
                        const holdingsDiv = document.getElementById('holdings-data');
                        let tableHTML = `
                            <table class="holdings-table">
                                <thead>
                                    <tr><th>Symbol</th><th>Qty</th><th>Price</th><th>Value</th><th>Day %</th><th>P&L %</th></tr>
                                </thead>
                                <tbody>
                        `;
                        
                        holdings.forEach(holding => {
                            const dayChangeClass = holding.day_change_pct >= 0 ? 'positive' : 'negative';
                            const pnlClass = holding.unrealized_pnl_pct >= 0 ? 'positive' : 'negative';
                            
                            tableHTML += `
                                <tr>
                                    <td>${holding.symbol}</td>
                                    <td>${holding.quantity}</td>
                                    <td>₹${holding.current_price.toFixed(0)}</td>
                                    <td>₹${holding.value.toLocaleString()}</td>
                                    <td class="${dayChangeClass}">${holding.day_change_pct > 0 ? '+' : ''}${holding.day_change_pct.toFixed(1)}%</td>
                                    <td class="${pnlClass}">${holding.unrealized_pnl_pct > 0 ? '+' : ''}${holding.unrealized_pnl_pct.toFixed(1)}%</td>
                                </tr>
                            `;
                        });
                        
                        tableHTML += '</tbody></table>';
                        holdingsDiv.innerHTML = tableHTML;
                    }
                    
                    function refreshData() {
                        fetch('/api/portfolio')
                            .then(response => response.json())
                            .then(data => {
                                updatePortfolioStatus(data);
                                updateRiskStatus(data);
                                updateHoldings(data.holdings);
                                document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                            })
                            .catch(error => {
                                console.error('Error fetching data:', error);
                            });
                        
                        // Update auth status and profile
                        updateAuthStatus();
                        updateUserProfile();
                    }
                    
                    function updateUserProfile() {
                        fetch('/api/profile')
                            .then(response => response.json())
                            .then(data => {
                                const profileDiv = document.getElementById('user-profile');
                                
                                if (data.authenticated && data.user_name) {
                                    profileDiv.innerHTML = `👤 Welcome, ${data.user_name} (${data.user_id})`;
                                    
                                    // Update header subtitle if authenticated with real data
                                    const subtitleDiv = document.getElementById('header-subtitle');
                                    if (!data.cached) {
                                        subtitleDiv.textContent = 'Autonomous Family Office System - Live Portfolio';
                                    } else {
                                        subtitleDiv.textContent = 'Autonomous Family Office System - Cached Session';
                                    }
                                } else {
                                    profileDiv.innerHTML = '';
                                    document.getElementById('header-subtitle').textContent = 'Autonomous Family Office System';
                                }
                            })
                            .catch(error => {
                                console.error('Error fetching profile:', error);
                                document.getElementById('user-profile').innerHTML = '';
                            });
                    }
                    
                    function updateAuthStatus() {
                        // First check cookies
                        fetch('/api/auth/check-cookies')
                            .then(response => response.json())
                            .then(cookieData => {
                                const authDiv = document.getElementById('auth-status');
                                const authDetailsDiv = document.getElementById('auth-details');
                                const loginBtn = document.getElementById('login-btn');
                                const logoutBtn = document.getElementById('logout-btn');
                                
                                if (cookieData.authenticated) {
                                    authDiv.innerHTML = '<span style="color: green;">✅ Authenticated via Cookies</span>';
                                    
                                    // Try to get user info from cookie
                                    let userInfo = '';
                                    try {
                                        const userInfoCookie = getCookie('kite_user_info');
                                        if (userInfoCookie) {
                                            const userDetails = JSON.parse(userInfoCookie);
                                            userInfo = `<strong>User:</strong> ${userDetails.user_name} (${userDetails.user_id})<br>`;
                                        } else if (cookieData.user_name) {
                                            userInfo = `<strong>User:</strong> ${cookieData.user_name} (${cookieData.user_id})<br>`;
                                        }
                                    } catch (e) {
                                        if (cookieData.user_name) {
                                            userInfo = `<strong>User:</strong> ${cookieData.user_name} (${cookieData.user_id})<br>`;
                                        }
                                    }
                                    
                                    authDetailsDiv.innerHTML = userInfo + `<small>Expires in ${cookieData.days_remaining} days</small>`;
                                    loginBtn.style.display = 'none';
                                    logoutBtn.style.display = 'inline-block';
                                    return;
                                }
                                
                                // If no valid cookies, check server status
                                return fetch('/api/status');
                            })
                            .then(response => {
                                if (!response) return; // Already handled cookie auth above
                                return response.json();
                            })
                            .then(data => {
                                if (!data) return; // Already handled cookie auth above
                                
                                const authDiv = document.getElementById('auth-status');
                                const authDetailsDiv = document.getElementById('auth-details');
                                const loginBtn = document.getElementById('login-btn');
                                const logoutBtn = document.getElementById('logout-btn');
                                
                                if (data.mock_mode) {
                                    authDiv.innerHTML = '<span style="color: orange;">📋 Mock Mode Active</span>';
                                    authDetailsDiv.innerHTML = '<small>Using sample data for demonstration</small>';
                                    loginBtn.style.display = 'inline-block';
                                    logoutBtn.style.display = 'none';
                                } else {
                                    authDiv.innerHTML = '<span style="color: green;">✅ Connected to Kite</span>';
                                    authDetailsDiv.innerHTML = '<small>Using real portfolio data</small>';
                                    loginBtn.style.display = 'none';
                                    logoutBtn.style.display = 'inline-block';
                                }
                            })
                            .catch(error => {
                                console.error('Error checking auth status:', error);
                                const authDiv = document.getElementById('auth-status');
                                const loginBtn = document.getElementById('login-btn');
                                const logoutBtn = document.getElementById('logout-btn');
                                
                                authDiv.innerHTML = '<span style="color: red;">❌ Auth Check Failed</span>';
                                loginBtn.style.display = 'inline-block';
                                logoutBtn.style.display = 'none';
                            });
                    }
                    
                    // Helper function to get cookie value
                    function getCookie(name) {
                        const value = `; ${document.cookie}`;
                        const parts = value.split(`; ${name}=`);
                        if (parts.length === 2) return parts.pop().split(';').shift();
                        return null;
                    }
                    
                    function clearAuthCookies() {
                        // Call logout API
                        fetch('/api/auth/logout', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            }
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                // Clear client-side cookies as well (belt and suspenders)
                                document.cookie = 'kite_request_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                                document.cookie = 'kite_access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                                document.cookie = 'kite_auth_timestamp=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                                document.cookie = 'kite_user_info=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                                
                                // Show logout success message
                                const authDiv = document.getElementById('auth-status');
                                authDiv.innerHTML = '<span style="color: green;">✅ Logged out successfully</span>';
                                
                                // Refresh the page after a brief delay
                                setTimeout(() => {
                                    location.reload();
                                }, 1000);
                            } else {
                                console.error('Logout failed:', data.message);
                                alert('Logout failed: ' + data.message);
                            }
                        })
                        .catch(error => {
                            console.error('Logout error:', error);
                            // Fallback: clear cookies manually and refresh
                            document.cookie = 'kite_request_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                            document.cookie = 'kite_access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                            document.cookie = 'kite_auth_timestamp=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                            document.cookie = 'kite_user_info=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                            location.reload();
                        });
                    }
                    
                    function authenticateKite() {
                        fetch('/api/auth/login-url')
                            .then(response => response.json())
                            .then(data => {
                                if (data.login_url) {
                                    const authWindow = window.open(data.login_url, '_blank', 'width=600,height=700');
                                    
                                    // Check if auth window is closed (successful auth)
                                    const checkClosed = setInterval(() => {
                                        if (authWindow.closed) {
                                            clearInterval(checkClosed);
                                            setTimeout(() => {
                                                // Refresh all data including profile
                                                refreshData();
                                                updateUserProfile();
                                            }, 2000);
                                        }
                                    }, 1000);
                                } else {
                                    alert('Error: ' + (data.error || 'Unable to generate login URL'));
                                }
                            })
                            .catch(error => {
                                console.error('Error:', error);
                                alert('Authentication failed');
                            });
                    }
                    
                    function analyzeStock() {
                        const symbol = document.getElementById('symbol-input').value.toUpperCase();
                        const resultDiv = document.getElementById('analysis-result');
                        
                        if (!symbol) {
                            resultDiv.innerHTML = '<p style="color: red;">Please enter a symbol</p>';
                            return;
                        }
                        
                        resultDiv.innerHTML = '<p>Analyzing...</p>';
                        
                        fetch(`/api/analyze/${symbol}`)
                            .then(response => response.json())
                            .then(data => {
                                const verdictColor = data.verdict === 'THESIS_INTACT' ? 'positive' : 
                                                   data.verdict === 'CYCLICAL_PAIN' ? '#f39c12' : 'negative';
                                
                                resultDiv.innerHTML = `
                                    <div style="margin-top: 15px; padding: 10px; background: white; border-radius: 4px;">
                                        <h4>${symbol} Analysis</h4>
                                        <p><strong>Verdict:</strong> <span style="color: ${verdictColor};">${data.verdict}</span></p>
                                        <p><strong>Confidence:</strong> ${(data.confidence * 100).toFixed(0)}%</p>
                                        <p><strong>Reasoning:</strong> ${data.reasoning}</p>
                                    </div>
                                `;
                            })
                            .catch(error => {
                                resultDiv.innerHTML = '<p style="color: red;">Analysis failed</p>';
                                console.error('Error:', error);
                            });
                    }
                    
                    // Auto-refresh every 30 seconds
                    setInterval(refreshData, 30000);
                    
                    // Initial load
                    refreshData();
                    updateUserProfile();
                </script>
            </body>
            </html>
            '''
        
        @self.app.route('/api/status')
        def api_status():
            """API endpoint for system status"""
            return jsonify({
                'timestamp': datetime.now().isoformat(),
                'status': 'active',
                'mock_mode': self.config.system.mock_mode,
                'market_hours': self.config.is_market_hours(),
                'system_health': 'operational'
            })
        
        @self.app.route('/api/auth/check-cookies')
        def api_auth_check_cookies():
            """Check if user has valid authentication cookies"""
            try:
                from flask import request
                
                request_token = request.cookies.get('kite_request_token')
                access_token = request.cookies.get('kite_access_token')
                auth_timestamp = request.cookies.get('kite_auth_timestamp')
                
                if request_token and access_token and auth_timestamp:
                    # Check if tokens are still valid (30 days)
                    auth_time = datetime.fromtimestamp(int(auth_timestamp))
                    if datetime.now() - auth_time < timedelta(days=30):
                        
                        # Verify token by checking if it can be used
                        try:
                            from kiteconnect import KiteConnect
                            api_key = self.config.zerodha.api_key
                            kite = KiteConnect(api_key=api_key)
                            kite.set_access_token(access_token)
                            
                            # Quick test to verify token validity
                            profile = kite.profile()
                            
                            return jsonify({
                                'authenticated': True,
                                'user_name': profile.get('user_name', 'Unknown'),
                                'user_id': profile.get('user_id', 'Unknown'),
                                'auth_timestamp': auth_timestamp,
                                'days_remaining': (30 - (datetime.now() - auth_time).days)
                            })
                            
                        except Exception as token_error:
                            logger.warning(f"Stored token invalid: {token_error}")
                            return jsonify({
                                'authenticated': False,
                                'reason': 'Token validation failed',
                                'need_reauth': True
                            })
                    else:
                        return jsonify({
                            'authenticated': False,
                            'reason': 'Tokens expired',
                            'need_reauth': True
                        })
                else:
                    return jsonify({
                        'authenticated': False,
                        'reason': 'No stored tokens found',
                        'need_reauth': True
                    })
                    
            except Exception as e:
                logger.error(f"Cookie auth check error: {e}")
                return jsonify({
                    'authenticated': False,
                    'error': str(e),
                    'need_reauth': True
                }), 500
        
        @self.app.route('/api/auth/logout', methods=['POST'])
        def api_auth_logout():
            """Logout endpoint to clear authentication cookies and .env tokens"""
            try:
                from flask import make_response
                
                # Clear .env file tokens
                env_path = '.env'
                if os.path.exists(env_path):
                    with open(env_path, 'r') as f:
                        lines = f.readlines()
                    
                    # Clear tokens in .env
                    for i, line in enumerate(lines):
                        if line.startswith('KITE_REQUEST_TOKEN='):
                            lines[i] = 'KITE_REQUEST_TOKEN=\n'
                        elif line.startswith('KITE_ACCESS_TOKEN='):
                            lines[i] = 'KITE_ACCESS_TOKEN=\n'
                    
                    with open(env_path, 'w') as f:
                        f.writelines(lines)
                
                # Create response
                response = make_response(jsonify({
                    'success': True,
                    'message': 'Logged out successfully'
                }))
                
                # Clear all authentication cookies
                response.set_cookie('kite_request_token', '', expires=0, path='/')
                response.set_cookie('kite_access_token', '', expires=0, path='/')
                response.set_cookie('kite_auth_timestamp', '', expires=0, path='/')
                
                logger.info("🚪 User logged out successfully")
                return response
                
            except Exception as e:
                logger.error(f"Logout error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/auth/login-url')
        def api_auth_login_url():
            """Generate Kite Connect login URL"""
            try:
                api_key = self.config.zerodha.api_key
                if api_key and api_key != 'your_api_key_here':
                    login_url = f'https://kite.zerodha.com/connect/login?api_key={api_key}&v=3'
                    return jsonify({
                        'login_url': login_url,
                        'instructions': {
                            'step1': 'Click the login URL to authenticate with Zerodha',
                            'step2': 'You will be redirected back automatically after login',
                            'step3': 'Refresh this page to see your real holdings'
                        }
                    })
                else:
                    return jsonify({'error': 'API key not configured'}), 400
            except Exception as e:
                logger.error(f"Login URL generation error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/profile')
        def api_profile():
            """Get user profile information"""
            try:
                from flask import request
                
                # Try to get access token from cookies
                access_token = request.cookies.get('kite_access_token')
                user_info_cookie = request.cookies.get('kite_user_info')
                
                if access_token:
                    try:
                        # Create temporary Kite session with cookie token
                        from kiteconnect import KiteConnect
                        api_key = self.config.zerodha.api_key
                        kite = KiteConnect(api_key=api_key)
                        kite.set_access_token(access_token)
                        
                        # Get fresh profile data
                        profile = kite.profile()
                        return jsonify({
                            'authenticated': True,
                            'profile': profile,
                            'user_name': profile.get('user_name', 'Unknown'),
                            'user_id': profile.get('user_id', 'Unknown'),
                            'email': profile.get('email', 'Unknown'),
                            'broker': profile.get('broker', 'Zerodha')
                        })
                        
                    except Exception as e:
                        logger.warning(f"Failed to fetch profile with cookie token: {e}")
                        # Fallback to cached user info
                        if user_info_cookie:
                            try:
                                user_info = json.loads(user_info_cookie)
                                return jsonify({
                                    'authenticated': True,
                                    'profile': user_info,
                                    'user_name': user_info.get('user_name', 'Unknown'),
                                    'user_id': user_info.get('user_id', 'Unknown'),
                                    'email': user_info.get('email', 'Unknown'),
                                    'cached': True
                                })
                            except:
                                pass
                
                return jsonify({
                    'authenticated': False,
                    'error': 'No valid authentication found'
                })
                
            except Exception as e:
                logger.error(f"Profile API error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/portfolio')
        def api_portfolio():
            """API endpoint for portfolio data"""
            try:
                from flask import request
                
                # Try to get access token from cookies first
                access_token = request.cookies.get('kite_access_token')
                
                if access_token and self.governor:
                    # Use the Governor's built-in token support
                    portfolio_data = self.governor.audit_risk(access_token=access_token)
                    logger.info("Portfolio data fetched using cookie authentication")
                    return jsonify(portfolio_data)
                
                # Fallback to regular governor (might be mock mode)
                if self.governor:
                    portfolio_data = self.governor.audit_risk()
                    return jsonify(portfolio_data)
                else:
                    return jsonify({'error': 'Governor not initialized'}), 500
                    
            except Exception as e:
                logger.error(f"Portfolio API error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/analyze/<symbol>')
        def api_analyze(symbol):
            """API endpoint for stock analysis"""
            try:
                if self.scout:
                    result = self.scout.analyze_ticker(symbol, 'web_request')
                    return jsonify({
                        'symbol': result.symbol,
                        'verdict': result.verdict.value,
                        'confidence': result.confidence,
                        'reasoning': result.reasoning,
                        'timestamp': result.timestamp.isoformat()
                    })
                else:
                    return jsonify({'error': 'Scout not initialized'}), 500
            except Exception as e:
                logger.error(f"Analysis API error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/auth/callback')
        def auth_callback():
            """Handle Kite Connect authentication callback"""
            try:
                from flask import request, make_response
                request_token = request.args.get('request_token')
                status = request.args.get('status')
                
                if status == 'success' and request_token:
                    # Generate access token
                    access_token = None
                    user_profile = None
                    try:
                        from kiteconnect import KiteConnect
                        api_key = self.config.zerodha.api_key
                        api_secret = self.config.zerodha.api_secret
                        
                        kite = KiteConnect(api_key=api_key)
                        data = kite.generate_session(request_token, api_secret=api_secret)
                        access_token = data['access_token']
                        
                        # Get user profile
                        kite.set_access_token(access_token)
                        user_profile = kite.profile()
                        
                        logger.info(f"✅ Access token generated for user: {user_profile.get('user_name', 'Unknown')}")
                    except Exception as token_error:
                        logger.error(f"Failed to generate access token: {token_error}")
                        return make_response(f'''
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>Authentication Failed</title>
                            <style>
                                body {{ 
                                    font-family: Arial, sans-serif; 
                                    padding: 40px; 
                                    text-align: center; 
                                    background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
                                    color: white;
                                    min-height: 100vh;
                                    margin: 0;
                                    display: flex;
                                    align-items: center;
                                    justify-content: center;
                                }}
                                .container {{
                                    background: rgba(255,255,255,0.1);
                                    padding: 30px;
                                    border-radius: 10px;
                                    backdrop-filter: blur(10px);
                                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                                }}
                            </style>
                        </head>
                        <body>
                            <div class="container">
                                <h1>❌ Authentication Failed</h1>
                                <p>Failed to generate access token.</p>
                                <p>Error: {token_error}</p>
                                <button onclick="window.close()" style="padding: 10px 20px; background: white; color: #c0392b; border: none; border-radius: 5px; cursor: pointer;">Close Window</button>
                            </div>
                        </body>
                        </html>
                        ''')
                    
                    if access_token:
                        # Create response with success page
                        response_html = f'''
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>Authentication Success</title>
                            <style>
                                body {{ 
                                    font-family: Arial, sans-serif; 
                                    padding: 40px; 
                                    text-align: center; 
                                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                    color: white;
                                    min-height: 100vh;
                                    margin: 0;
                                    display: flex;
                                    align-items: center;
                                    justify-content: center;
                                }}
                                .container {{
                                    background: rgba(255,255,255,0.1);
                                    padding: 30px;
                                    border-radius: 10px;
                                    backdrop-filter: blur(10px);
                                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                                }}
                            </style>
                        </head>
                        <body>
                            <div class="container">
                                <h1>🎉 Authentication Successful!</h1>
                                <p>Welcome, {user_profile.get('user_name', 'User') if user_profile else 'User'}!</p>
                                <p><strong>User ID:</strong> {user_profile.get('user_id', 'Unknown') if user_profile else 'Unknown'}</p>
                                <p>🔐 Authentication tokens securely stored in cookies.</p>
                                <p>The dashboard will now use your real holdings.</p>
                                <p><small>This window will close automatically in 3 seconds...</small></p>
                                <script>
                                    setTimeout(() => {{
                                        window.close();
                                        // If window doesn't close (some browsers), redirect to dashboard
                                        if (!window.closed) {{
                                            window.location.href = '/';
                                        }}
                                    }}, 3000);
                                </script>
                            </div>
                        </body>
                        </html>
                        '''
                        
                        # Create response with cookies (NO .env storage)
                        response = make_response(response_html)
                        
                        # Set secure cookies with 30-day expiration
                        expire_date = datetime.now() + timedelta(days=30)
                        
                        response.set_cookie(
                            'kite_request_token', 
                            request_token, 
                            expires=expire_date,
                            httponly=True,
                            secure=False,  # Set to True in production with HTTPS
                            samesite='Lax',
                            path='/'
                        )
                        
                        response.set_cookie(
                            'kite_access_token', 
                            access_token, 
                            expires=expire_date,
                            httponly=True,
                            secure=False,  # Set to True in production with HTTPS
                            samesite='Lax',
                            path='/'
                        )
                        
                        response.set_cookie(
                            'kite_auth_timestamp', 
                            str(int(datetime.now().timestamp())), 
                            expires=expire_date,
                            httponly=False,  # Allow JS access for timestamp checks
                            secure=False,
                            samesite='Lax',
                            path='/'
                        )
                        
                        # Store user info in cookie for display
                        if user_profile:
                            response.set_cookie(
                                'kite_user_info', 
                                json.dumps({
                                    'user_name': user_profile.get('user_name', 'Unknown'),
                                    'user_id': user_profile.get('user_id', 'Unknown'),
                                    'email': user_profile.get('email', 'Unknown')
                                }), 
                                expires=expire_date,
                                httponly=False,  # Allow JS access for display
                                secure=False,
                                samesite='Lax',
                                path='/'
                            )
                        
                        logger.info(f"✅ Authentication successful! Tokens stored in cookies only")
                        return response
                    
                else:
                    logger.error(f"Authentication failed: {request.args}")
                    error_html = '''
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Authentication Failed</title>
                        <style>
                            body {{ 
                                font-family: Arial, sans-serif; 
                                padding: 40px; 
                                text-align: center; 
                                background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
                                color: white;
                                min-height: 100vh;
                                margin: 0;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                            }}
                            .container {{
                                background: rgba(255,255,255,0.1);
                                padding: 30px;
                                border-radius: 10px;
                                backdrop-filter: blur(10px);
                                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>❌ Authentication Failed</h1>
                            <p>There was an error with the authentication process.</p>
                            <p>Please try again or check your credentials.</p>
                            <button onclick="window.close()" style="padding: 10px 20px; background: white; color: #c0392b; border: none; border-radius: 5px; cursor: pointer;">Close Window</button>
                        </div>
                    </body>
                    </html>
                    '''
                    return make_response(error_html)
                    
            except Exception as e:
                logger.error(f"Auth callback error: {e}")
                return jsonify({'error': str(e)}), 500
    
    def _initialize_system(self):
        """Initialize system components"""
        try:
            logger.info("Initializing Mosaic Vault web system...")
            
            # Check for cookie-based authentication first
            cookie_auth_success = False
            
            # Note: In a real Flask context, we'd have access to request.cookies
            # For initialization, we'll try .env first, then rely on cookie checks in routes
            if not self.config.system.mock_mode:
                try:
                    self.kite_session = get_kite_session()
                    logger.info("Kite session established")
                except Exception as e:
                    logger.warning(f"Kite authentication failed during init: {e}")
                    # Don't set mock mode here - let individual requests handle cookie auth
            
            # Initialize Governor (will handle auth per request)
            self.governor = Governor(self.kite_session)
            
            # Set up Governor with credentials for cookie-based auth
            api_key = os.getenv('KITE_API_KEY')
            api_secret = os.getenv('KITE_API_SECRET')
            
            if api_key and api_secret:
                self.governor.set_credentials(api_key, api_secret)
                logger.info("✅ Governor configured with API credentials for cookie auth")
            
            logger.info("System initialized successfully")
            
        except Exception as e:
            logger.error(f"System initialization failed: {e}")
    
    def run(self):
        """Run the web dashboard"""
        try:
            logger.info(f"🌐 Starting Mosaic Vault Web Dashboard")
            logger.info(f"🔗 Open your browser to: http://localhost:{self.port}")
            self.app.run(host='0.0.0.0', port=self.port, debug=self.debug)
        except KeyboardInterrupt:
            logger.info("Web dashboard stopped by user")
        except Exception as e:
            logger.error(f"Web dashboard failed: {e}")

def run_web_dashboard(port: int = 5000, debug: bool = False):
    """Run the web dashboard"""
    dashboard = WebDashboard(port=port, debug=debug)
    dashboard.run()