# Inversion Capital — On-Chain Diligence Pipeline

**[Live App →](https://hussain0327-on-chain-research-pipeline.streamlit.app)**

Evaluates whether stablecoin payment infrastructure is a viable value creation lever for PE acquisition targets. Pulls live on-chain data from DeFiLlama, runs cost comparison models with configurable assumptions, and outputs IC-ready tear sheets.

Built to support thesis generation for businesses where legacy financial infrastructure suppresses margins.

---

## What It Does

**Business Diligence** — Input a target company's financials and payment profile. The pipeline projects 12-month Web2 vs. Web3 costs, calculates EBITDA margin expansion and valuation uplift, runs sensitivity analysis across gas fee volatility and revenue growth scenarios, and compares chain ecosystem health. Includes quick scenario presets (Telecom MVNO, Freight Broker, Regional Bank), a conversion tier toggle (institutional 0.3% / blended 0.5% / retail 1.0%), and a phased rollout model that ramps adoption from 20% to 80% over 6 months. Outputs downloadable tear sheets and CSV exports.

**Protocol Screening** — Scores DeFi protocols across 5 dimensions (TVL strength, revenue quality, multi-chain presence, capital efficiency, volume activity) to assess whether chain infrastructure is mature enough to support a portfolio company migration.

**Market Scanner** — Precalculated savings across 6 verticals with thesis strength ratings, live stablecoin supply data with 6-month trends, and a chain comparison matrix covering transaction cost, settlement time, TVL, and stablecoin supply.

---

## Key Assumptions

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| Conversion tier | Blended (0.5%) | Assumes Circle Mint or OTC desk access, not retail on-ramp |
| Adoption curve | 20% → 80% over 6 months | Phased rollout with 20% of volume permanently on legacy rails |
| Migration cost | Tiered by revenue band | Sub-$5M: ~$96K, $5-10M: ~$160K, $10M+: ~$240K |
| EV multiple | 8-10x EBITDA | Standard lower-middle-market range |
| Gas fees | Live from DeFiLlama | Hardcoded fallbacks in config.py |

---

## Data Source

All on-chain data from [DeFiLlama's free API](https://defillama.com/docs/api). No API key required.

---

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Tests

```bash
python -m pytest tests/
```

---

## Project Structure

```
├── app.py                  # Streamlit app (primary deliverable)
├── pipeline.py             # CLI entry point
├── config.py               # Cost benchmarks, conversion tiers, migration costs
├── extract/
│   ├── defillama_client.py # DeFiLlama API client (retry, cache, rate limit)
│   └── stablecoin_metrics.py
├── transform/
│   ├── pe_feasibility.py   # Cost comparison, EBITDA impact, sensitivity
│   └── screening.py        # Protocol scoring, business case generation
├── load/
│   ├── csv_export.py
│   └── tearsheet.py        # Plotly tear sheet generator
└── tests/
    └── test_pipeline.py    # Unit tests (pure math, no API calls)
```
