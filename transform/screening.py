"""
Protocol screening and investment case generation for Inversion Capital.
"""

from extract.stablecoin_metrics import StablecoinInfraMetrics
from transform.pe_feasibility import FeasibilityAnalyzer


def screen_protocol_as_target(snapshot):
    """
    Score a protocol across 5 dimensions (0-100 each) against Inversion criteria.
    Input: snapshot dict from StablecoinInfraMetrics.get_protocol_health_snapshot()
    """
    scores = {}

    # 1. TVL strength (0-100): >$1B = 100, log scale down
    tvl = snapshot.get("total_tvl", 0) or 0
    if tvl >= 1_000_000_000:
        scores["tvl_strength"] = 100
    elif tvl >= 100_000_000:
        scores["tvl_strength"] = 70 + 30 * (tvl - 100_000_000) / 900_000_000
    elif tvl >= 10_000_000:
        scores["tvl_strength"] = 40 + 30 * (tvl - 10_000_000) / 90_000_000
    else:
        scores["tvl_strength"] = max(0, 40 * tvl / 10_000_000)

    # 2. Revenue quality (0-100): based on daily fees
    daily_fees = snapshot.get("daily_fees") or 0
    annualized_fees = daily_fees * 365
    if annualized_fees >= 50_000_000:
        scores["revenue_quality"] = 100
    elif annualized_fees >= 10_000_000:
        scores["revenue_quality"] = 60 + 40 * (annualized_fees - 10_000_000) / 40_000_000
    elif annualized_fees >= 1_000_000:
        scores["revenue_quality"] = 30 + 30 * (annualized_fees - 1_000_000) / 9_000_000
    else:
        scores["revenue_quality"] = max(0, 30 * annualized_fees / 1_000_000)

    # 3. Multi-chain presence (0-100): more chains = more resilient
    num_chains = len(snapshot.get("chains", []))
    scores["multi_chain"] = min(100, num_chains * 10)

    # 4. Capital efficiency (0-100): mcap/TVL ratio (lower is better for value)
    ratio = snapshot.get("mcap_tvl_ratio")
    if ratio is not None and ratio > 0:
        if ratio < 0.5:
            scores["capital_efficiency"] = 100
        elif ratio < 1.0:
            scores["capital_efficiency"] = 70 + 30 * (1.0 - ratio) / 0.5
        elif ratio < 3.0:
            scores["capital_efficiency"] = 30 + 40 * (3.0 - ratio) / 2.0
        else:
            scores["capital_efficiency"] = max(0, 30 * (10.0 - ratio) / 7.0)
    else:
        scores["capital_efficiency"] = 50  # neutral if no data

    # 5. Volume activity (0-100)
    daily_vol = snapshot.get("daily_volume") or 0
    if daily_vol >= 1_000_000_000:
        scores["volume_activity"] = 100
    elif daily_vol >= 100_000_000:
        scores["volume_activity"] = 60 + 40 * (daily_vol - 100_000_000) / 900_000_000
    elif daily_vol >= 1_000_000:
        scores["volume_activity"] = 20 + 40 * (daily_vol - 1_000_000) / 99_000_000
    elif daily_vol > 0:
        scores["volume_activity"] = 20 * daily_vol / 1_000_000
    else:
        scores["volume_activity"] = 0

    composite = sum(scores.values()) / len(scores)

    return {
        "slug": snapshot.get("slug", ""),
        "name": snapshot.get("name", ""),
        "scores": scores,
        "composite_score": round(composite, 1),
        "recommendation": (
            "Strong Buy" if composite >= 80 else
            "Buy" if composite >= 60 else
            "Hold" if composite >= 40 else
            "Pass"
        ),
    }


def screen_multiple_protocols(slugs, client=None):
    """Batch screening, sorted by composite score."""
    metrics = StablecoinInfraMetrics(client)
    results = []
    for slug in slugs:
        try:
            snapshot = metrics.get_protocol_health_snapshot(slug)
            result = screen_protocol_as_target(snapshot)
            results.append(result)
        except Exception as e:
            results.append({
                "slug": slug,
                "name": slug,
                "scores": {},
                "composite_score": 0,
                "recommendation": f"Error: {e}",
            })
    results.sort(key=lambda x: x["composite_score"], reverse=True)
    return results


def generate_traditional_business_case(company_profile, client=None):
    """
    Full investment case dict combining feasibility analysis + chain health.
    This is the glue function for the tear sheet.
    """
    analyzer = FeasibilityAnalyzer(company_profile)
    metrics = StablecoinInfraMetrics(client)

    cost_comparison = analyzer.calculate_cost_comparison()
    ebitda_impact = analyzer.calculate_ebitda_impact()
    sensitivity = analyzer.run_sensitivity_analysis()

    # Get chain health data
    chain_analysis = metrics.get_comparative_chain_analysis()

    # Get supply trend for context
    try:
        supply_trend = metrics.get_stablecoin_supply_trend(stablecoin_id=1, days=90)
    except Exception:
        supply_trend = None

    return {
        "company_profile": company_profile,
        "cost_comparison": cost_comparison,
        "ebitda_impact": ebitda_impact,
        "sensitivity": sensitivity,
        "chain_analysis": chain_analysis,
        "supply_trend": supply_trend,
    }
