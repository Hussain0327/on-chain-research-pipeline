# Inversion Capital — On-Chain Diligence Pipeline

**[Live App →](https://inversion-diligence-pipeline.streamlit.app)**

Evaluates whether stablecoin payment infrastructure is a viable value creation lever for PE acquisition targets. Pulls live on-chain data from DeFiLlama, runs cost comparison models with configurable assumptions, and outputs IC-ready tear sheets.

Built to support thesis generation for businesses where legacy financial infrastructure suppresses margins.

---

## What It Does

**Business Diligence** — Input a target company's financials and payment profile. The pipeline projects 12-month Web2 vs. Web3 costs, calculates EBITDA margin expansion and valuation uplift, and runs sensitivity analysis across gas fee volatility and revenue growth scenarios. Includes quick scenario presets (Telecom MVNO, Freight Broker, Regional Bank), side-by-side chain comparison, conversion tier selection (institutional / blended / retail), and a phased rollout model that ramps adoption from 20% to 80% over 6 months. Outputs downloadable tear sheets and CSV exports.

**Protocol Screening** — Scores DeFi protocols across 5 dimensions (TVL strength, revenue quality, multi-chain presence, capital efficiency, volume activity) to assess whether chain infrastructure is mature enough to support a portfolio company migration.

**Market Scanner** — Precalculated savings across 6 verticals with thesis strength ratings, live stablecoin supply data with 6-month trends, and a chain comparison matrix covering transaction cost, settlement time, TVL, and stablecoin supply.

---

## Sample Output: Freight Broker

$8M revenue, 10% EBITDA margin, 6,000 carrier payments/month at $2,500 avg, wire transfer to Avalanche USDC, blended conversion tier, phased rollout.

| Metric                | Value                |
| --------------------- | -------------------- |
| Annual Savings        | $582,660             |
| Margin Expansion      | 728 bps (10% → ~17%) |
| Payback Period        | 4.1 months           |
| Year 1 ROI            | 191%                 |
| Valuation Uplift (8x) | $4.66M               |

Savings represent 32% of total Web2 payment costs ($1.8M/year in wire fees). Phased rollout ramps from 20% adoption in month 1 to 80% by month 6, with breakeven at month 6.

---

## Key Assumptions

| Parameter       | Default                       | Rationale                                                       |
| --------------- | ----------------------------- | --------------------------------------------------------------- |
| Conversion tier | Blended (0.5%)                | Assumes Circle Mint or OTC desk access, not retail on-ramp      |
| Adoption curve  | 20% → 80% over 6 months       | Phased rollout; 20% of volume stays on legacy rails permanently |
| Migration cost  | Tiered by revenue             | Sub-$5M: ~$96K / $5-10M: ~$160K / $10M+: ~$240K                 |
| EV multiple     | 8x EBITDA                     | Lower-middle-market range                                       |
| Gas fees        | Live from DeFiLlama           | Hardcoded fallbacks in config.py                                |
| Savings cap     | Cannot exceed total Web2 cost | Sanity guard prevents impossible outputs                        |

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

18 tests covering cost model math, screening logic, savings caps, adoption curve validation, and a freight broker regression test.

---

## Project Structure

```
├── app.py                    # Streamlit app (primary deliverable)
├── pipeline.py               # CLI entry point
├── config.py                 # Cost benchmarks, conversion tiers, migration costs
├── extract/
│   ├── defillama_client.py   # DeFiLlama API client (retry, cache, rate limit)
│   └── stablecoin_metrics.py
├── transform/
│   ├── pe_feasibility.py     # Cost comparison, EBITDA impact, sensitivity
│   └── screening.py          # Protocol scoring, infrastructure readiness
├── load/
│   ├── csv_export.py
│   └── tearsheet.py          # Plotly tear sheet generator
└── tests/
    └── test_pipeline.py      # 18 unit + regression tests (no API calls)
```
