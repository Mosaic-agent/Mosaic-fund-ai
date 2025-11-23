"""
Mosaic Vault - Notification System
Handles WhatsApp alerts via CallMeBot API (free tier).
"""

import requests
import time
from typing import Optional
from datetime import datetime
from urllib.parse import quote_plus
from config import get_config
import logging

logger = logging.getLogger(__name__)

class NotificationError(Exception):
    """Custom exception for notification failures"""
    pass

class WhatsAppNotifier:
    """
    WhatsApp notification system using CallMeBot API
    Zero cost implementation for critical alerts
    """
    
    def __init__(self):
        self.config = get_config()
        self.base_url = "https://api.callmebot.com/whatsapp.php"
        self.rate_limit_delay = 2.0  # Seconds between messages
        self.last_message_time = 0.0
        
    def _rate_limit(self) -> None:
        """Implement rate limiting to avoid spam"""
        current_time = time.time()
        time_since_last = current_time - self.last_message_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_message_time = time.time()
    
    def send_message(self, message: str, urgent: bool = False) -> bool:
        """
        Send WhatsApp message via CallMeBot
        
        Args:
            message: Message text to send
            urgent: If true, bypasses some rate limiting
            
        Returns:
            bool: True if message sent successfully
        """
        if not self.config.notifications.enabled:
            logger.debug("Notifications disabled, skipping message")
            return False
        
        try:
            if not urgent:
                self._rate_limit()
            
            # Prepare message with timestamp
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"🏛️ Mosaic Vault [{timestamp}]\n{message}"
            
            # CallMeBot API parameters
            params = {
                'phone': self.config.notifications.whatsapp_number,
                'apikey': self.config.notifications.callmebot_api_key,
                'text': formatted_message
            }
            
            # Send request
            response = requests.get(self.base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"WhatsApp message sent successfully")
                return True
            else:
                logger.error(f"WhatsApp message failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"WhatsApp notification failed: {e}")
            return False
    
    def send_risk_alert(self, zone: str, portfolio_value: float, 
                       drawdown: float, action: str) -> bool:
        """Send risk zone alert"""
        zone_emojis = {
            'GREEN': '🟢',
            'YELLOW': '🟡', 
            'RED': '🔴'
        }
        
        emoji = zone_emojis.get(zone, '⚪')
        
        message = f"""{emoji} RISK ALERT {emoji}

Zone: {zone}
Portfolio: ₹{portfolio_value:,.0f}
Drawdown: {drawdown:.1f}%

Action Required:
{action}

Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"""
        
        return self.send_message(message, urgent=(zone == 'RED'))
    
    def send_thesis_alert(self, symbol: str, verdict: str, 
                         action: str, confidence: float) -> bool:
        """Send thesis violation alert"""
        verdict_emojis = {
            'THESIS_INTACT': '✅',
            'CYCLICAL_PAIN': '⚠️',
            'STRUCTURAL_DECAY': '❌'
        }
        
        emoji = verdict_emojis.get(verdict, '❓')
        
        message = f"""{emoji} THESIS ALERT

Stock: {symbol}
Verdict: {verdict}
Confidence: {confidence:.0%}

Recommended Action:
{action}

Scout Analysis Complete"""
        
        return self.send_message(message)
    
    def send_system_alert(self, alert_type: str, details: str) -> bool:
        """Send system status alert"""
        alert_emojis = {
            'ERROR': '❌',
            'WARNING': '⚠️',
            'INFO': 'ℹ️',
            'SUCCESS': '✅'
        }
        
        emoji = alert_emojis.get(alert_type.upper(), '📢')
        
        message = f"""{emoji} SYSTEM ALERT

Type: {alert_type.upper()}
Details: {details}

Mosaic Vault System"""
        
        return self.send_message(message, urgent=(alert_type.upper() == 'ERROR'))
    
    def send_daily_summary(self, portfolio_value: float, day_change: float,
                          top_performers: list, bottom_performers: list) -> bool:
        """Send daily portfolio summary"""
        change_emoji = "📈" if day_change >= 0 else "📉"
        
        message = f"""📊 DAILY SUMMARY

Portfolio: ₹{portfolio_value:,.0f}
Day Change: {change_emoji} {day_change:+.1f}%

🔝 Top Performers:
{chr(10).join([f"• {stock}" for stock in top_performers[:3]])}

🔻 Bottom Performers:
{chr(10).join([f"• {stock}" for stock in bottom_performers[:3]])}

Risk Status: Monitoring"""
        
        return self.send_message(message)

class AlertManager:
    """
    Central alert management system
    Coordinates different types of notifications
    """
    
    def __init__(self):
        self.whatsapp = WhatsAppNotifier()
        self.alert_history = []
        
    def send_alert(self, alert_type: str, **kwargs) -> bool:
        """
        Send alert via appropriate channel
        
        Args:
            alert_type: Type of alert (risk, thesis, system, summary)
            **kwargs: Alert-specific parameters
        """
        success = False
        
        try:
            if alert_type == 'risk':
                success = self.whatsapp.send_risk_alert(**kwargs)
            elif alert_type == 'thesis':
                success = self.whatsapp.send_thesis_alert(**kwargs)
            elif alert_type == 'system':
                success = self.whatsapp.send_system_alert(**kwargs)
            elif alert_type == 'summary':
                success = self.whatsapp.send_daily_summary(**kwargs)
            else:
                logger.error(f"Unknown alert type: {alert_type}")
                return False
            
            # Log alert
            self.alert_history.append({
                'timestamp': datetime.now(),
                'type': alert_type,
                'success': success,
                'kwargs': kwargs
            })
            
            return success
            
        except Exception as e:
            logger.error(f"Alert sending failed: {e}")
            return False
    
    def get_alert_history(self, limit: int = 10) -> list:
        """Get recent alert history"""
        return sorted(
            self.alert_history, 
            key=lambda x: x['timestamp'], 
            reverse=True
        )[:limit]

# Global alert manager instance
alert_manager = AlertManager()

# Convenience functions
def send_risk_alert(zone: str, portfolio_value: float, drawdown: float, action: str) -> bool:
    """Send risk zone alert"""
    return alert_manager.send_alert('risk', 
                                  zone=zone, 
                                  portfolio_value=portfolio_value,
                                  drawdown=drawdown, 
                                  action=action)

def send_thesis_alert(symbol: str, verdict: str, action: str, confidence: float) -> bool:
    """Send thesis violation alert"""
    return alert_manager.send_alert('thesis',
                                  symbol=symbol,
                                  verdict=verdict, 
                                  action=action,
                                  confidence=confidence)

def send_system_alert(alert_type: str, details: str) -> bool:
    """Send system alert"""
    return alert_manager.send_alert('system',
                                  alert_type=alert_type,
                                  details=details)

if __name__ == "__main__":
    """Test notification system"""
    print("Testing Mosaic Vault Notification System...")
    
    # Test system alert
    result = send_system_alert("INFO", "Notification system test")
    print(f"System alert sent: {result}")
    
    # Test risk alert  
    result = send_risk_alert("YELLOW", 150000, 6.5, "Trim high-beta positions")
    print(f"Risk alert sent: {result}")
    
    print("Test complete")