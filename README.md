# Inversion Capital — On-Chain Diligence Pipeline

ETL pipeline and Streamlit app for evaluating stablecoin payment infrastructure as a PE value creation lever. Pulls live on-chain data from DeFiLlama, translates it into PE metrics (EBITDA impact, cost savings, payback period), and outputs Investment Committee-ready tear sheets.

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## App Tabs

### Business Diligence
Input a target company's financials and payment profile. The pipeline calculates:
- 12-month Web2 vs Web3 cost projection
- EBITDA margin expansion and valuation uplift
- Sensitivity analysis across fee volatility and growth scenarios
- Chain ecosystem health comparison

Includes quick scenario presets (Telecom MVNO, Freight Broker, Regional Bank), side-by-side chain comparison, and downloadable tear sheets.

### Protocol Screening
Score DeFi protocols across 5 dimensions (TVL strength, revenue quality, multi-chain presence, capital efficiency, volume activity) against Inversion's acquisition criteria.

### Market Scanner
- **Savings by Sector** — precalculated savings for 6 verticals with thesis strength ratings
- **Stablecoin Infrastructure Dashboard** — live supply data, 6-month trends
- **Chain Comparison Matrix** — tx cost, settlement time, TVL, stablecoin supply across chains

## CLI

```bash
# Full business diligence with tear sheet
python pipeline.py --mode business --name "TargetCo" --revenue 5000000 \
  --ebitda-margin 0.15 --monthly-tx 50000 --avg-tx-value 60 \
  --payment-method credit_card --target-chain avalanche_usdc

# Protocol screening
python pipeline.py --mode protocol --slugs aave-v3,lido,sky-lending
```

## Project Structure

```
├── app.py                  # Streamlit app (primary deliverable)
├── pipeline.py             # CLI entry point
├── config.py               # Cost benchmarks, API URLs, migration costs
├── extract/
│   ├── defillama_client.py # DeFiLlama API client (retry, cache, rate limit)
│   └── stablecoin_metrics.py # Higher-level stablecoin analytics
├── transform/
│   ├── pe_feasibility.py   # Cost comparison, EBITDA impact, sensitivity
│   └── screening.py        # Protocol scoring, business case generation
├── load/
│   ├── csv_export.py       # CSV export functions
│   └── tearsheet.py        # Plotly tear sheet generator
└── tests/
    └── test_pipeline.py    # Unit tests (pure math, no API calls)
```

## Data Source

All on-chain data comes from [DeFiLlama's free API](https://defillama.com/docs/api) — no API key required.

## Tests

```bash
python -m pytest tests/
```
