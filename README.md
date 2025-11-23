# Mosaic 

Mosaic is an autonomous, agentic AI Fund Manager designed to grant Financial Sovereignty to the individual investor. It bridges the capability gap between retail traders and institutional hedge funds by providing a "Risk Committee" and "Research Analyst" that runs locally on your machine at zero operational cost.

**The Mosaic Theory**: The method of analysis used by security analysts to gather information about a corporation from a variety of sources—public, non-public, and non-material—to determine the underlying value of its securities.

## 1. The Mission: Individual Empowerment

**The Game is Rigged.**

Institutional investors possess three distinct advantages over the individual: Information (Analyst Teams), Discipline (Risk Committees), and Execution (Algorithmic Models). The retail investor, conversely, relies on emotions, tips, and static SIPs that fail to account for market valuations.

**Mosaic exists to level the playing field.**

It acts as an "Iron Man Suit" for your capital. It does not replace the human investor; it protects and enhances them. It empowers a single individual to manage a portfolio with the rigor of a professional fund, ensuring that decisions are data-backed, risk-adjusted, and emotion-free.

## 2. The Problem & The Opportunity

### The Scenario: Leveraged Capital

This project is built to solve a specific, high-stakes financial challenge: Managing a Leveraged Portfolio.

- **The Capital**: Borrowed funds (₹7 Lakhs).
- **The Cost**: 7.65% Interest Rate.
- **The Constraint**: 24-Month Horizon.

### The Challenge

To succeed, the portfolio must not only generate returns but also:

- **Beat the Hurdle Rate**: Outperform the 7.65% cost of debt significantly.
- **Self-Fund**: Generate enough internal liquidity to service monthly interest payments without eroding capital.
- **Preserve Capital**: Avoid drawdown risks that could wipe out equity in a leveraged setup.

### The "India Advantage"

We are seizing a unique window of opportunity:

- **Free Compute**: Google has unlocked Gemini 1.5 Pro for free in India. This allows us to process thousands of pages of Annual Reports and Financial Results without paying the typical enterprise AI costs ($1000+/month).
- **Free Data**: By utilizing a stack of Zero-Brokerage APIs (Shoonya/Angel One) and open-source libraries, we reduce the Operational Expense (Opex) to Zero.

## 3. Strategic Objectives

### A. The "Zero Opex" Mandate

Every rupee spent on software subscriptions or data feeds increases the breakeven hurdle. Mosaic is engineered to run entirely on Free Tier infrastructure.

- **Database**: Local Storage (SQLite/JSON).
- **Compute**: Local Machine / Free Cloud Tiers.
- **Intelligence**: Gemini CLI via OAuth.

### B. Human-Centric Sovereignty (Human-in-the-Loop)

Mosaic is not a "Black Box" trading bot. It operates on a CIO/CFO model:

- **You (The CIO)**: You provide the "Watchlist" and the investment thesis.
- **Mosaic (The CFO)**: The AI validates your ideas against hard data, enforces risk limits, and manages the cash flow. It has Veto Power over bad investments (e.g., High Debt companies) to protect you from yourself.

### C. The "Self-Funding" Mechanism

The system manages a Two-Bucket Cash Strategy to ensure solvency:

- **Liquid Reserve (Opex)**: Keeps 3 months of interest payments in Liquid ETFs to service the loan.
- **War Chest (Opportunity)**: Parks uninvested capital in Arbitrage Funds/Liquid BeES to offset the "Negative Carry" of the loan while waiting for market opportunities.

## 4. High-Level Architecture

Mosaic operates as a Unified Control Plane composed of three distinct AI Agents ("The Council") that deliberate before any money moves.

### The Council of Agents

| Agent | Role | Responsibility |
|-------|------|----------------|
| **The Accountant** | Quantitative Analyst | Analyzes "Hard Data" (Balance Sheets, P/E, Debt-to-Equity). strictly rejects companies that violate the Debt-Service Protocol (Debt > 0.5x). |
| **The Scout** | Qualitative Research | Reads PDF Annual Reports, Transcripts, and News using Gemini Pro. Detects governance risks, capex cycles, and management sentiment. |
| **The Governor** | Risk & Allocation | The decision engine. Calculates the "Conviction Multiplier" and determines the exact SIP/STP Ratio. It enforces the "Core-Satellite" strategy (ETFs for safety, Stocks for alpha). |

### The Workflow (The DAG)

1. **Ingestion**: System fetches market data and corporate filings for your Watchlist.
2. **Validation**: The Accountant checks financial health. The Scout checks news sentiment.
3. **Deliberation**: If fundamentals are weak, the stock is Vetoed. If strong, a "Conviction Score" is assigned.
4. **Allocation**: The Governor calculates the optimal monthly deployment (Smart STP) based on market valuation (buying more when cheap, less when expensive).
5. **Execution**: The user receives a specific "Action Plan" (e.g., "Buy 40% NiftyBeES, 30% Tata Power, Hold 30% Liquid").

## Documentation

For detailed component documentation, please refer to the [`docs/`](./docs/) folder.

---

## ⚠️ Disclaimer

Mosaic is an educational project and a research tool. It is not a SEBI-registered investment advisor. The logic provided is for simulation and decision-support only. Managing leveraged capital involves significant risk.