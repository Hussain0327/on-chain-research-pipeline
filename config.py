"""
Configuration constants for the on-chain diligence pipeline.
"""

# DeFiLlama API base URLs
DEFILLAMA_BASE_URL = "https://api.llama.fi"
DEFILLAMA_STABLECOINS_URL = "https://stablecoins.llama.fi"

# Web2 cost benchmarks (annual, per-transaction or fixed)
WEB2_COSTS = {
    "credit_card": {
        "processing_rate": 0.029,  # 2.9% per transaction
        "per_tx_fee": 0.30,  # $0.30 per transaction
        "monthly_platform_fee": 500,  # $500/mo for payment platform
        "chargeback_rate": 0.006,  # 0.6% chargeback rate
        "chargeback_fee": 15.00,  # $15 per chargeback
    },
    "wire_transfer": {
        "per_tx_fee": 25.00,  # $25 per wire
        "monthly_platform_fee": 200,
        "processing_rate": 0.0,
        "chargeback_rate": 0.0,
        "chargeback_fee": 0.0,
    },
    "ach": {
        "processing_rate": 0.008,  # 0.8%
        "per_tx_fee": 0.25,
        "monthly_platform_fee": 100,
        "chargeback_rate": 0.003,
        "chargeback_fee": 5.00,
    },
    "cross_border": {
        "processing_rate": 0.035,  # 3.5% FX + processing
        "per_tx_fee": 15.00,  # SWIFT/intermediary fees
        "monthly_platform_fee": 750,
        "chargeback_rate": 0.002,
        "chargeback_fee": 25.00,
    },
}

# Web3 cost benchmarks (per chain, per-transaction)
WEB3_COSTS = {
    "ethereum_usdc": {
        "avg_gas_fee": 3.50,  # avg gas cost per transfer in USD
        "bridge_fee_rate": 0.001,  # 0.1% for bridging
        "onramp_fee_rate": 0.015,  # 1.5% fiat on-ramp
        "smart_contract_audit": 50000,  # one-time audit cost
        "monthly_infra": 300,  # node/RPC provider
    },
    "polygon_usdc": {
        "avg_gas_fee": 0.01,
        "bridge_fee_rate": 0.001,
        "onramp_fee_rate": 0.015,
        "smart_contract_audit": 50000,
        "monthly_infra": 200,
    },
    "arbitrum_usdc": {
        "avg_gas_fee": 0.10,
        "bridge_fee_rate": 0.001,
        "onramp_fee_rate": 0.015,
        "smart_contract_audit": 50000,
        "monthly_infra": 250,
    },
    "avalanche_usdc": {
        "avg_gas_fee": 0.05,
        "bridge_fee_rate": 0.001,
        "onramp_fee_rate": 0.015,
        "smart_contract_audit": 40000,
        "monthly_infra": 200,
    },
    "solana_usdc": {
        "avg_gas_fee": 0.005,
        "bridge_fee_rate": 0.002,
        "onramp_fee_rate": 0.015,
        "smart_contract_audit": 45000,
        "monthly_infra": 250,
    },
    "base_usdc": {
        "avg_gas_fee": 0.02,
        "bridge_fee_rate": 0.001,
        "onramp_fee_rate": 0.015,
        "smart_contract_audit": 40000,
        "monthly_infra": 200,
    },
}

# One-time migration costs
MIGRATION_COSTS = {
    "assessment_30d": 15000,
    "infrastructure_build_60d": 75000,
    "migration_cutover_30d": 30000,
    "compliance_legal": 30000,
    "staff_training": 10000,
    "parallel_run_months": 3,
    "ongoing_monthly_ops": 2000,
}

# Pipeline defaults
DEFAULT_CACHE_TTL = 300  # 5 minutes in seconds
DEFAULT_RATE_LIMIT = 0.5  # seconds between API calls
DEFAULT_RETRIES = 3
