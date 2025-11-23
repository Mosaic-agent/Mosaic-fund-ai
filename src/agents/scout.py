"""
Mosaic Vault - The Scout (Forensic Analyst)
Handles thesis validation and headwind detection using Gemini CLI.
Implements the "Tri-Vector" intelligence model for investment analysis.
"""

import subprocess
import json
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import yfinance as yf

# Configure logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

class AnalysisVerdict(Enum):
    """Scout analysis verdicts"""
    THESIS_INTACT = "THESIS_INTACT"      # Temporary fear - buying opportunity
    CYCLICAL_PAIN = "CYCLICAL_PAIN"      # Industry-wide challenges - trim 50%
    STRUCTURAL_DECAY = "STRUCTURAL_DECAY" # Permanent impairment - exit 100%
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA" # Unable to determine
    ERROR = "ERROR"                       # Analysis failed

@dataclass
class AnalysisResult:
    """Result of Scout analysis"""
    symbol: str
    verdict: AnalysisVerdict
    confidence: float  # 0.0 to 1.0
    reasoning: str
    triggers: List[str]  # What caused the analysis
    timestamp: datetime
    data_sources: List[str]

class GeminiCLI:
    """
    Interface to Google Gemini CLI for zero-cost intelligence.
    Handles subprocess calls to the Gemini command line tool.
    """
    
    def __init__(self):
        self.cli_command = "gemini"  # Assumes Gemini CLI is installed and configured
        self.rate_limit_delay = 1.0  # Delay between calls to respect rate limits
        self.last_call_time = 0.0
        
    def _check_cli_availability(self) -> bool:
        """Check if Gemini CLI is available and authenticated"""
        try:
            result = subprocess.run(
                [self.cli_command, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _rate_limit(self) -> None:
        """Implement rate limiting to stay within free tier"""
        current_time = time.time()
        time_since_last = current_time - self.last_call_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_call_time = time.time()
    
    def run_analysis(self, prompt: str, format_type: str = "json") -> Dict:
        """
        Execute Gemini analysis via CLI
        
        Args:
            prompt: The analysis prompt
            format_type: Response format ('json', 'text')
            
        Returns:
            Dict: Gemini response or error
        """
        if not self._check_cli_availability():
            return {
                "error": "Gemini CLI not available",
                "success": False
            }
        
        self._rate_limit()
        
        try:
            # Construct CLI command - new format for Gemini CLI
            cmd = [
                self.cli_command,
                "--output-format", format_type,
                prompt
            ]
            
            logger.debug(f"Executing Gemini CLI: {' '.join(cmd[:3])}...")
            
            # Execute with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            if result.returncode == 0:
                if format_type == "json":
                    try:
                        return {
                            "response": json.loads(result.stdout),
                            "success": True
                        }
                    except json.JSONDecodeError:
                        return {
                            "response": result.stdout,
                            "success": True,
                            "warning": "Response not valid JSON"
                        }
                else:
                    return {
                        "response": result.stdout,
                        "success": True
                    }
            else:
                logger.error(f"Gemini CLI error: {result.stderr}")
                return {
                    "error": result.stderr,
                    "success": False
                }
                
        except subprocess.TimeoutExpired:
            logger.error("Gemini CLI timeout")
            return {
                "error": "Analysis timeout",
                "success": False
            }
        except Exception as e:
            logger.error(f"Gemini CLI execution failed: {e}")
            return {
                "error": str(e),
                "success": False
            }

class Scout:
    """
    The Scout - Forensic Analyst Agent
    Implements thesis validation and headwind detection
    """
    
    def __init__(self):
        self.gemini = GeminiCLI()
        self.analysis_history = []
        
    def analyze_ticker(self, ticker: str, trigger_event: str = "price_drop", 
                      context: Dict = None) -> AnalysisResult:
        """
        Main analysis function - The Scout's core responsibility
        
        Args:
            ticker: Stock symbol to analyze
            trigger_event: What triggered the analysis
            context: Additional context (price drop %, news, etc.)
            
        Returns:
            AnalysisResult: Complete analysis with verdict and reasoning
        """
        try:
            logger.info(f"Scout analyzing {ticker} - Trigger: {trigger_event}")
            
            # Gather context data
            market_data = self._gather_market_data(ticker)
            
            # Run Tri-Vector analysis
            now_analysis = self._analyze_now(ticker, trigger_event, context)
            trend_analysis = self._analyze_trend(ticker, market_data)
            consensus_analysis = self._analyze_consensus(ticker)
            
            # Combine analyses and determine verdict
            final_verdict = self._synthesize_verdict(
                ticker, now_analysis, trend_analysis, consensus_analysis
            )
            
            # Create result
            result = AnalysisResult(
                symbol=ticker,
                verdict=final_verdict["verdict"],
                confidence=final_verdict["confidence"],
                reasoning=final_verdict["reasoning"],
                triggers=[trigger_event],
                timestamp=datetime.now(),
                data_sources=["Gemini CLI", "Yahoo Finance", "Market Data"]
            )
            
            # Store in history
            self.analysis_history.append(result)
            logger.info(f"Scout analysis complete: {ticker} = {result.verdict.value}")
            
            return result
            
        except Exception as e:
            logger.error(f"Scout analysis failed for {ticker}: {e}")
            return AnalysisResult(
                symbol=ticker,
                verdict=AnalysisVerdict.ERROR,
                confidence=0.0,
                reasoning=f"Analysis failed: {str(e)}",
                triggers=[trigger_event],
                timestamp=datetime.now(),
                data_sources=[]
            )
    
    def _gather_market_data(self, ticker: str) -> Dict:
        """Gather market data using free sources"""
        try:
            # Get data from Yahoo Finance
            stock = yf.Ticker(f"{ticker}.NS")
            
            # Current info
            info = stock.info
            history = stock.history(period="1mo")
            
            if history.empty:
                return {}
            
            current_price = history['Close'].iloc[-1]
            price_52w_high = history['High'].max() 
            price_52w_low = history['Low'].min()
            
            # Calculate recent performance
            price_1d = history['Close'].iloc[-1] if len(history) >= 1 else current_price
            price_5d = history['Close'].iloc[-5] if len(history) >= 5 else current_price
            price_1m = history['Close'].iloc[0] if len(history) >= 20 else current_price
            
            return {
                "current_price": current_price,
                "price_change_1d": (current_price - price_1d) / price_1d * 100,
                "price_change_5d": (current_price - price_5d) / price_5d * 100,
                "price_change_1m": (current_price - price_1m) / price_1m * 100,
                "52w_high": price_52w_high,
                "52w_low": price_52w_low,
                "distance_from_high": (price_52w_high - current_price) / price_52w_high * 100,
                "distance_from_low": (current_price - price_52w_low) / price_52w_low * 100,
                "avg_volume": history['Volume'].mean(),
                "current_volume": history['Volume'].iloc[-1],
                "market_cap": info.get("marketCap", 0),
                "pe_ratio": info.get("trailingPE", 0),
                "sector": info.get("sector", "Unknown")
            }
            
        except Exception as e:
            logger.warning(f"Market data gathering failed for {ticker}: {e}")
            return {}
    
    def _analyze_now(self, ticker: str, trigger_event: str, context: Dict) -> Dict:
        """
        Vector 1: The Now - Real-time event analysis
        Analyzes immediate news and events affecting the stock
        """
        try:
            # Construct prompt for current situation analysis
            prompt = f"""
            Analyze the current situation for stock {ticker}.
            
            Trigger Event: {trigger_event}
            Context: {json.dumps(context) if context else 'None'}
            
            Please search for recent news about {ticker} and classify the situation:
            
            1. TEMPORARY - Short-term fear (fire at plant, strike, regulatory inquiry, etc.)
            2. CYCLICAL - Industry-wide challenges (commodity prices, sector rotation, etc.)  
            3. STRUCTURAL - Permanent business impairment (technology disruption, management issues, debt crisis)
            
            Respond in JSON format:
            {{
                "classification": "TEMPORARY|CYCLICAL|STRUCTURAL",
                "confidence": 0.0-1.0,
                "key_news": ["list of relevant news items"],
                "reasoning": "detailed explanation",
                "risk_factors": ["list of identified risks"],
                "timeframe": "how long this situation might last"
            }}
            """
            
            result = self.gemini.run_analysis(prompt, "json")
            
            if result["success"] and isinstance(result["response"], dict):
                return result["response"]
            else:
                return {
                    "classification": "INSUFFICIENT_DATA",
                    "confidence": 0.0,
                    "reasoning": "Unable to analyze current situation",
                    "error": result.get("error", "Unknown error")
                }
                
        except Exception as e:
            logger.error(f"'Now' analysis failed for {ticker}: {e}")
            return {
                "classification": "ERROR",
                "confidence": 0.0,
                "reasoning": f"Analysis error: {str(e)}"
            }
    
    def _analyze_trend(self, ticker: str, market_data: Dict) -> Dict:
        """
        Vector 2: The Trend - Historical context analysis
        Analyzes long-term trends and valuation context
        """
        try:
            if not market_data:
                return {
                    "trend_signal": "NEUTRAL",
                    "confidence": 0.0,
                    "reasoning": "Insufficient market data"
                }
            
            # Construct trend analysis prompt
            prompt = f"""
            Analyze the historical trend and valuation context for {ticker}.
            
            Market Data:
            - Current Price: {market_data.get('current_price', 'N/A')}
            - 1D Change: {market_data.get('price_change_1d', 0):.2f}%
            - 5D Change: {market_data.get('price_change_5d', 0):.2f}%
            - 1M Change: {market_data.get('price_change_1m', 0):.2f}%
            - 52W High: {market_data.get('52w_high', 'N/A')}
            - 52W Low: {market_data.get('52w_low', 'N/A')}
            - Distance from High: {market_data.get('distance_from_high', 0):.2f}%
            - PE Ratio: {market_data.get('pe_ratio', 'N/A')}
            - Sector: {market_data.get('sector', 'Unknown')}
            
            Based on this data, determine:
            1. Is this price level historically CHEAP, FAIR, or EXPENSIVE?
            2. What is the cyclical position (EARLY_CYCLE, MID_CYCLE, LATE_CYCLE)?
            3. Is this a good entry point from a valuation perspective?
            
            Respond in JSON format:
            {{
                "valuation_signal": "CHEAP|FAIR|EXPENSIVE",
                "cyclical_position": "EARLY_CYCLE|MID_CYCLE|LATE_CYCLE",
                "entry_quality": "EXCELLENT|GOOD|FAIR|POOR",
                "confidence": 0.0-1.0,
                "key_metrics": ["relevant valuation insights"],
                "reasoning": "detailed valuation analysis"
            }}
            """
            
            result = self.gemini.run_analysis(prompt, "json")
            
            if result["success"] and isinstance(result["response"], dict):
                return result["response"]
            else:
                return {
                    "valuation_signal": "NEUTRAL",
                    "confidence": 0.0,
                    "reasoning": "Unable to analyze trend data"
                }
                
        except Exception as e:
            logger.error(f"'Trend' analysis failed for {ticker}: {e}")
            return {
                "trend_signal": "ERROR",
                "confidence": 0.0,
                "reasoning": f"Trend analysis error: {str(e)}"
            }
    
    def _analyze_consensus(self, ticker: str) -> Dict:
        """
        Vector 3: The Consensus - Institutional flow analysis
        Analyzes what smart money is doing in this sector
        """
        try:
            # Construct institutional flow analysis prompt
            prompt = f"""
            Analyze institutional sentiment and flow for {ticker} and its sector.
            
            Search for recent information about:
            1. Mutual fund buying/selling in this stock or sector
            2. FII/DII activity patterns
            3. Sector rotation trends
            4. Institutional research reports or upgrades/downgrades
            
            Determine if institutions are:
            - BUYING (increasing positions)
            - SELLING (reducing positions) 
            - NEUTRAL (no clear direction)
            
            Respond in JSON format:
            {{
                "institutional_stance": "BUYING|SELLING|NEUTRAL",
                "flow_strength": "STRONG|MODERATE|WEAK",
                "confidence": 0.0-1.0,
                "key_flows": ["list of institutional activities"],
                "sector_rotation": "description of sector trends",
                "reasoning": "detailed institutional analysis"
            }}
            """
            
            result = self.gemini.run_analysis(prompt, "json")
            
            if result["success"] and isinstance(result["response"], dict):
                return result["response"]
            else:
                return {
                    "institutional_stance": "NEUTRAL",
                    "confidence": 0.0,
                    "reasoning": "Unable to analyze institutional flows"
                }
                
        except Exception as e:
            logger.error(f"'Consensus' analysis failed for {ticker}: {e}")
            return {
                "institutional_stance": "ERROR",
                "confidence": 0.0,
                "reasoning": f"Consensus analysis error: {str(e)}"
            }
    
    def _synthesize_verdict(self, ticker: str, now: Dict, trend: Dict, consensus: Dict) -> Dict:
        """
        Synthesize the three vectors into a final verdict
        This is where the Scout makes the crucial decision
        """
        try:
            # Extract classifications
            now_class = now.get("classification", "INSUFFICIENT_DATA")
            trend_signal = trend.get("valuation_signal", "NEUTRAL")
            consensus_stance = consensus.get("institutional_stance", "NEUTRAL")
            
            # Calculate weighted confidence
            confidences = [
                now.get("confidence", 0.0),
                trend.get("confidence", 0.0), 
                consensus.get("confidence", 0.0)
            ]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Decision logic based on tri-vector analysis
            verdict = AnalysisVerdict.INSUFFICIENT_DATA
            reasoning_parts = []
            
            # Primary decision based on 'now' analysis
            if now_class == "STRUCTURAL":
                verdict = AnalysisVerdict.STRUCTURAL_DECAY
                reasoning_parts.append("Structural damage detected")
            elif now_class == "CYCLICAL":
                verdict = AnalysisVerdict.CYCLICAL_PAIN
                reasoning_parts.append("Cyclical headwinds identified")
            elif now_class == "TEMPORARY":
                # Check if it's a buying opportunity based on other vectors
                if trend_signal == "CHEAP" and consensus_stance in ["BUYING", "NEUTRAL"]:
                    verdict = AnalysisVerdict.THESIS_INTACT
                    reasoning_parts.append("Temporary fear + attractive valuation = opportunity")
                else:
                    verdict = AnalysisVerdict.THESIS_INTACT
                    reasoning_parts.append("Temporary issue, thesis remains intact")
            
            # Adjust based on trend and consensus
            if trend_signal == "EXPENSIVE" and verdict == AnalysisVerdict.THESIS_INTACT:
                verdict = AnalysisVerdict.CYCLICAL_PAIN
                reasoning_parts.append("Expensive valuation warrants caution")
            
            if consensus_stance == "SELLING" and verdict == AnalysisVerdict.THESIS_INTACT:
                avg_confidence *= 0.8  # Reduce confidence if institutions are selling
                reasoning_parts.append("Institutional selling noted")
            
            # Compile reasoning
            reasoning = f"{ticker} analysis: " + "; ".join(reasoning_parts)
            reasoning += f". Now={now_class}, Trend={trend_signal}, Consensus={consensus_stance}"
            
            return {
                "verdict": verdict,
                "confidence": min(avg_confidence, 1.0),
                "reasoning": reasoning,
                "vector_summary": {
                    "now": now_class,
                    "trend": trend_signal, 
                    "consensus": consensus_stance
                }
            }
            
        except Exception as e:
            logger.error(f"Verdict synthesis failed for {ticker}: {e}")
            return {
                "verdict": AnalysisVerdict.ERROR,
                "confidence": 0.0,
                "reasoning": f"Synthesis error: {str(e)}"
            }
    
    def run_headwind_check(self, ticker: str, price_drop_pct: float) -> Dict:
        """
        Specialized headwind detection for significant price drops
        This is called when a stock drops >5% or other trigger events occur
        """
        context = {
            "price_drop_pct": price_drop_pct,
            "trigger_threshold": 5.0,
            "analysis_type": "headwind_detection"
        }
        
        result = self.analyze_ticker(ticker, "price_drop", context)
        
        # Convert to action-oriented response
        action_map = {
            AnalysisVerdict.THESIS_INTACT: "HOLD",
            AnalysisVerdict.CYCLICAL_PAIN: "TRIM", 
            AnalysisVerdict.STRUCTURAL_DECAY: "EXIT",
            AnalysisVerdict.INSUFFICIENT_DATA: "MONITOR",
            AnalysisVerdict.ERROR: "MANUAL_REVIEW"
        }
        
        return {
            "symbol": ticker,
            "verdict": result.verdict.value,
            "action": action_map[result.verdict],
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "price_drop": price_drop_pct,
            "timestamp": result.timestamp.isoformat()
        }
    
    def get_analysis_history(self, ticker: str = None, limit: int = 10) -> List[Dict]:
        """Get recent analysis history"""
        history = self.analysis_history
        
        if ticker:
            history = [a for a in history if a.symbol == ticker]
        
        # Sort by timestamp (most recent first)
        history.sort(key=lambda x: x.timestamp, reverse=True)
        
        return [
            {
                "symbol": a.symbol,
                "verdict": a.verdict.value,
                "confidence": a.confidence,
                "reasoning": a.reasoning,
                "timestamp": a.timestamp.isoformat()
            }
            for a in history[:limit]
        ]

# Convenience functions
def analyze_ticker(ticker: str, trigger_event: str = "manual", context: Dict = None) -> Dict:
    """Convenience function for direct ticker analysis"""
    scout = Scout()
    result = scout.analyze_ticker(ticker, trigger_event, context)
    
    return {
        "symbol": result.symbol,
        "verdict": result.verdict.value,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
        "timestamp": result.timestamp.isoformat()
    }

def headwind_check(ticker: str, price_drop_pct: float) -> Dict:
    """Quick headwind detection for price drops"""
    scout = Scout()
    return scout.run_headwind_check(ticker, price_drop_pct)

if __name__ == "__main__":
    """Test the scout module"""
    # Test with a sample ticker
    logger.info("Testing Scout with sample analysis...")
    
    # Test basic analysis
    result = analyze_ticker("RELIANCE", "test_run")
    print(f"Analysis Result: {result['verdict']}")
    print(f"Reasoning: {result['reasoning']}")
    
    # Test headwind detection
    headwind_result = headwind_check("TCS", -6.5)
    print(f"Headwind Check: {headwind_result['action']}")
    print(f"Confidence: {headwind_result['confidence']:.1%}")