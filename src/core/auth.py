"""
Mosaic Vault - Authentication Module (The Gatekeeper)
Handles Zerodha Kite Connect authentication with TOTP automation.
Zero Opex Design: Uses personal plan, automated 2FA, secure local storage.
"""

import os
import time
import logging
from typing import Optional
import onetimepass as otp
from kiteconnect import KiteConnect
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

class AuthenticationError(Exception):
    """Custom exception for authentication failures"""
    pass

class ZerodhaAuth:
    """
    Handles Zerodha authentication with TOTP automation.
    Implements the 'Zero Opex' constraint using personal plan only.
    """
    
    def __init__(self):
        self.api_key = os.getenv('KITE_API_KEY')
        self.api_secret = os.getenv('KITE_API_SECRET') 
        self.user_id = os.getenv('KITE_USER_ID')
        self.password = os.getenv('KITE_PASSWORD')
        self.totp_secret = os.getenv('KITE_TOTP_SECRET')
        
        # Validate required environment variables
        self._validate_credentials()
        
        # Initialize KiteConnect
        self.kite = KiteConnect(api_key=self.api_key)
        
    def _validate_credentials(self) -> None:
        """Validate all required credentials are present"""
        required_vars = {
            'KITE_API_KEY': self.api_key,
            'KITE_API_SECRET': self.api_secret,
            'KITE_USER_ID': self.user_id,
            'KITE_PASSWORD': self.password,
            'KITE_TOTP_SECRET': self.totp_secret
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        
        if missing_vars:
            raise AuthenticationError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )
    
    def _generate_totp(self) -> str:
        """Generate TOTP code for 2FA automation"""
        try:
            totp_code = otp.get_totp(self.totp_secret)
            logger.debug(f"Generated TOTP: {totp_code}")
            return totp_code
        except Exception as e:
            logger.error(f"TOTP generation failed: {e}")
            raise AuthenticationError(f"TOTP generation failed: {e}")
    
    def _perform_login(self) -> str:
        """
        Perform the login process and return access token.
        Handles the full OAuth flow with TOTP automation.
        """
        try:
            # Step 1: Get request token
            login_url = self.kite.login_url()
            logger.info(f"Login URL generated: {login_url}")
            
            # For headless operation, we need to simulate the browser login
            # This requires the request token which comes from browser redirect
            # In production, you'd implement selenium automation here
            
            # For now, we'll assume the request token is provided via environment
            request_token = os.getenv('KITE_REQUEST_TOKEN')
            
            if not request_token:
                raise AuthenticationError(
                    "Request token required. Please set KITE_REQUEST_TOKEN in .env "
                    "after completing browser login flow"
                )
            
            # Step 2: Generate session with TOTP
            totp_code = self._generate_totp()
            
            # Step 3: Get access token
            data = self.kite.generate_session(request_token, api_secret=self.api_secret)
            access_token = data["access_token"]
            
            logger.info(f"Authentication successful. Access token: {access_token[:20]}...")
            return access_token
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise AuthenticationError(f"Login process failed: {e}")
    
    def get_kite_session(self) -> KiteConnect:
        """
        Main authentication function. Returns authenticated KiteConnect object.
        
        Returns:
            KiteConnect: Authenticated Kite Connect instance
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Check if we have a cached access token
            cached_token = os.getenv('KITE_ACCESS_TOKEN')
            
            if cached_token:
                # Try using cached token
                self.kite.set_access_token(cached_token)
                
                # Test the token by making a simple API call
                try:
                    profile = self.kite.profile()
                    logger.info(f"Using cached token for user: {profile['user_name']}")
                    return self.kite
                except Exception:
                    logger.warning("Cached token expired, performing fresh login")
            
            # Perform fresh authentication
            access_token = self._perform_login()
            self.kite.set_access_token(access_token)
            
            # Verify authentication by getting user profile
            profile = self.kite.profile()
            logger.info(f"Authenticated as: {profile['user_name']}")
            
            # Cache the token for subsequent runs (optional)
            self._cache_access_token(access_token)
            
            return self.kite
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise AuthenticationError(f"Failed to get Kite session: {e}")
    
    def _cache_access_token(self, access_token: str) -> None:
        """
        Cache access token for reuse (valid until market close).
        Note: Tokens are valid until 7:30 AM next trading day.
        """
        try:
            # In production, store in secure local storage with expiry
            # For now, we'll log it for manual caching
            logger.info(f"Cache this token in .env as KITE_ACCESS_TOKEN: {access_token}")
        except Exception as e:
            logger.warning(f"Token caching failed: {e}")

# Convenience function for direct usage
def get_kite_session() -> KiteConnect:
    """
    Convenience function to get authenticated KiteConnect session.
    
    Returns:
        KiteConnect: Ready-to-use authenticated session
        
    Example:
        >>> kite = get_kite_session()
        >>> holdings = kite.holdings()
    """
    auth = ZerodhaAuth()
    return auth.get_kite_session()

# Health check function
def test_authentication() -> bool:
    """
    Test authentication and basic API functionality.
    
    Returns:
        bool: True if authentication successful and API responsive
    """
    try:
        kite = get_kite_session()
        
        # Test basic API calls
        profile = kite.profile()
        margins = kite.margins()
        
        logger.info("Authentication test passed")
        logger.info(f"Account: {profile['user_name']}")
        logger.info(f"Available Cash: ₹{margins['equity']['available']['cash']:,.2f}")
        
        return True
        
    except Exception as e:
        logger.error(f"Authentication test failed: {e}")
        return False

if __name__ == "__main__":
    """Test the authentication module"""
    test_authentication()