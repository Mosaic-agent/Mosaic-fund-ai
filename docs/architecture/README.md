# System Architecture

## Overview

Mosaic operates as a distributed system of AI agents that work together to provide autonomous fund management capabilities while maintaining human oversight.

## Core Components

### 1. Agent Framework
- **The Council**: Three specialized AI agents that deliberate on investment decisions
- **Communication Layer**: Inter-agent messaging and coordination
- **Decision Engine**: Consensus mechanism for final investment choices

### 2. Data Layer
- **Local Storage**: SQLite database for portfolio data and historical records
- **Market Data Pipeline**: Real-time and historical market data ingestion
- **Document Processing**: PDF parsing and analysis for annual reports

### 3. Risk Management System
- **Position Sizing**: Dynamic allocation based on conviction scores
- **Drawdown Protection**: Circuit breakers and stop-loss mechanisms
- **Leverage Monitoring**: Real-time debt service coverage tracking

### 4. Integration Layer
- **Broker APIs**: Zero-brokerage trading platform integration
- **AI Services**: Gemini Pro for document analysis and reasoning
- **External Data**: Market feeds and corporate filing sources

## Data Flow

```
Market Data → Ingestion → Agent Analysis → Risk Validation → Human Approval → Execution
```

## Security & Privacy

- All data processed locally
- No sensitive information sent to external services
- Encrypted storage for portfolio data
- API key management and rotation