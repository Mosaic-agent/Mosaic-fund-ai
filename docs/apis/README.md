# API Integration Guide

## Overview

Mosaic integrates with multiple APIs to gather market data and execute trades while maintaining zero operational costs.

## Supported Broker APIs

### Shoonya API
- **Provider**: Finvasia
- **Cost**: Zero brokerage
- **Features**: 
  - Real-time market data
  - Order placement and management
  - Portfolio tracking
  - Historical data access

### Angel One API
- **Provider**: Angel Broking
- **Cost**: Zero brokerage (conditions apply)
- **Features**:
  - Smart API integration
  - Market depth data
  - Technical indicators
  - Automated order execution

## Market Data Sources

### Free Data Providers
- **NSE/BSE**: Official exchange data
- **Yahoo Finance**: Historical and real-time data
- **Alpha Vantage**: Free tier for basic data
- **Quandl**: Economic and financial data

### Corporate Filings
- **BSE/NSE**: Annual reports and quarterly results
- **SEBI EDIFAR**: Regulatory filings
- **Company websites**: Investor relations data

## AI Services

### Google Gemini Pro
- **Usage**: Document analysis and reasoning
- **Cost**: Free tier in India
- **Capabilities**:
  - PDF parsing and summarization
  - Financial analysis
  - Natural language understanding
  - Multi-modal analysis

## Rate Limiting & Usage

- Implement exponential backoff for API calls
- Cache frequently accessed data locally
- Respect API rate limits to maintain free access
- Monitor usage to stay within free tiers