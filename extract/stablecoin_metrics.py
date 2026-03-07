"""
Higher-level stablecoin infrastructure metrics built on top of DeFiLlamaClient.
"""

import pandas as pd

from extract.defillama_client import DeFiLlamaClient


class StablecoinInfraMetrics:
    TRACKED_STABLECOINS = ["USDC", "USDT"]

    def __init__(self, client=None):
        self.client = client or DeFiLlamaClient()

    def get_stablecoin_supply_by_chain(self):
        """USDC/USDT circulating supply broken down by chain."""
        raw = self.client.get_stablecoins()
        stables = raw.get("peggedAssets", [])

        rows = []
        for stable in stables:
            symbol = stable.get("symbol", "")
            if symbol not in self.TRACKED_STABLECOINS:
                continue
            name = stable.get("name", symbol)
            chain_circ = stable.get("chainCirculating", {})
            for chain, data in chain_circ.items():
                current = data.get("current", {})
                supply = current.get("peggedUSD", 0)
                if supply > 0:
                    rows.append({
                        "stablecoin": symbol,
                        "name": name,
                        "chain": chain,
                        "circulating_supply_usd": supply,
                    })

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values("circulating_supply_usd", ascending=False).reset_index(drop=True)
        return df

    def get_chain_fee_economics(self):
        """Daily fee revenue per chain from the fees overview endpoint."""
        raw = self.client.get_fees_overview()
        protocols = raw.get("protocols", [])

        chain_fees = {}
        for protocol in protocols:
            chains = protocol.get("chains", [])
            daily_fees = protocol.get("dailyFees", 0) or 0
            total_fees_24h = protocol.get("total24h", 0) or 0
            fee_value = total_fees_24h if total_fees_24h else daily_fees
            if not fee_value:
                continue
            # Distribute evenly across chains as an approximation
            per_chain = fee_value / max(len(chains), 1)
            for chain in chains:
                chain_fees[chain] = chain_fees.get(chain, 0) + per_chain

        rows = [{"chain": chain, "estimated_daily_fees_usd": fees}
                for chain, fees in chain_fees.items()]
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values("estimated_daily_fees_usd", ascending=False).reset_index(drop=True)
        return df

    def get_stablecoin_supply_trend(self, stablecoin_id=1, days=90):
        """Historical supply trend for a given stablecoin (default: USDT, id=1)."""
        raw = self.client.get_stablecoin(stablecoin_id)
        tokens = raw.get("tokens", [])

        rows = []
        for entry in tokens[-days:]:
            date = entry.get("date", 0)
            circulating = entry.get("circulating", {}).get("peggedUSD", 0)
            rows.append({
                "date": pd.to_datetime(date, unit="s"),
                "circulating_supply_usd": circulating,
            })

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values("date").reset_index(drop=True)
        return df

    def _get_protocols_index(self):
        """Bulk fetch /protocols and index by slug. Cached at the client level."""
        if not hasattr(self, "_protocols_index"):
            raw = self.client.get_protocols()
            self._protocols_index = {p.get("slug", ""): p for p in raw}
        return self._protocols_index

    def get_protocol_health_snapshot(self, slug):
        """
        Unified protocol metrics dict using the lightweight bulk endpoint.
        Uses /protocols (bulk, cached) + /summary/fees/{slug} + /summary/dexs/{slug}.
        Does NOT call /protocol/{slug} (too heavy for screening).
        """
        index = self._get_protocols_index()
        protocol = index.get(slug)
        if protocol is None:
            raise ValueError(f"Protocol '{slug}' not found in DeFiLlama /protocols index")

        total_tvl = protocol.get("tvl", 0) or 0
        mcap = protocol.get("mcap") or 0

        snapshot = {
            "name": protocol.get("name", slug),
            "slug": slug,
            "category": protocol.get("category", "Unknown"),
            "chains": protocol.get("chains", []),
            "total_tvl": total_tvl,
            "chain_tvls": protocol.get("chainTvls", {}),
            "mcap_tvl_ratio": mcap / total_tvl if total_tvl else None,
            "change_1d": protocol.get("change_1d"),
            "change_7d": protocol.get("change_7d"),
            "change_1m": protocol.get("change_1m"),
        }

        # Lightweight fee call
        try:
            fees = self.client.get_protocol_fees(slug)
            snapshot["daily_fees"] = fees.get("total24h", 0)
            snapshot["daily_revenue"] = fees.get("totalRevenue24h", 0) or fees.get("total24h", 0)
        except Exception:
            snapshot["daily_fees"] = None
            snapshot["daily_revenue"] = None

        # Lightweight volume call
        try:
            vol = self.client.get_dex_volume(slug)
            snapshot["daily_volume"] = vol.get("total24h", 0)
        except Exception:
            snapshot["daily_volume"] = None

        return snapshot

    def get_comparative_chain_analysis(self, chains=None):
        """Multi-chain comparison table: TVL, stablecoin supply, fees."""
        if chains is None:
            chains = ["Ethereum", "Polygon", "Arbitrum", "Avalanche", "Solana"]

        # Chain TVLs
        all_chains = self.client.get_chains()
        chain_tvl_map = {c.get("name", ""): c.get("tvl", 0) for c in all_chains}

        # Stablecoin supply by chain
        supply_df = self.get_stablecoin_supply_by_chain()
        if not supply_df.empty:
            chain_supply = supply_df.groupby("chain")["circulating_supply_usd"].sum().to_dict()
        else:
            chain_supply = {}

        # Fee economics
        fee_df = self.get_chain_fee_economics()
        if not fee_df.empty:
            chain_fees = fee_df.set_index("chain")["estimated_daily_fees_usd"].to_dict()
        else:
            chain_fees = {}

        rows = []
        for chain in chains:
            rows.append({
                "chain": chain,
                "tvl": chain_tvl_map.get(chain, 0),
                "stablecoin_supply": chain_supply.get(chain, 0),
                "estimated_daily_fees": chain_fees.get(chain, 0),
                "stablecoin_tvl_ratio": (
                    chain_supply.get(chain, 0) / chain_tvl_map[chain]
                    if chain_tvl_map.get(chain, 0) > 0 else 0
                ),
            })

        return pd.DataFrame(rows)
