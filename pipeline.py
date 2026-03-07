"""
CLI entry point for the on-chain diligence pipeline.
"""

import argparse
import os
import sys

from extract.defillama_client import DeFiLlamaClient
from transform.screening import (
    screen_multiple_protocols,
    generate_traditional_business_case,
)
from load.csv_export import (
    export_cost_comparison,
    export_sensitivity,
    export_chain_analysis,
    export_screening_results,
)
from load.tearsheet import generate_tearsheet


def run_protocol_screening(slugs):
    """Screen protocols and output results."""
    print(f"\n{'='*60}")
    print("PROTOCOL SCREENING")
    print(f"{'='*60}")
    print(f"Screening {len(slugs)} protocols: {', '.join(slugs)}\n")

    client = DeFiLlamaClient()
    results = screen_multiple_protocols(slugs, client)

    output_dir = os.path.join("output", "screening")
    csv_path = export_screening_results(results, output_dir)

    for r in results:
        print(f"\n{'─'*40}")
        print(f"  {r['name']} ({r['slug']})")
        print(f"  Composite Score: {r['composite_score']}/100")
        print(f"  Recommendation:  {r['recommendation']}")
        if r.get("scores"):
            for dim, score in r["scores"].items():
                bar = "█" * int(score / 5) + "░" * (20 - int(score / 5))
                print(f"    {dim:25s} {bar} {score:.0f}")

    print(f"\n\nResults exported to: {csv_path}")
    return results


def run_business_diligence(profile):
    """Full diligence run with tear sheet."""
    print(f"\n{'='*60}")
    print(f"BUSINESS DILIGENCE: {profile['name']}")
    print(f"{'='*60}")

    client = DeFiLlamaClient()
    print("Fetching on-chain data...")
    case = generate_traditional_business_case(profile, client)

    output_dir = os.path.join("output", profile["name"].replace(" ", "_"))

    # Export CSVs
    print("Exporting analysis...")
    export_cost_comparison(case["cost_comparison"], output_dir)
    export_sensitivity(case["sensitivity"], output_dir)
    export_chain_analysis(case["chain_analysis"], output_dir)

    # Generate tear sheet
    print("Generating tear sheet...")
    html_path, png_path = generate_tearsheet(case, output_dir)

    # Print summary
    ebitda = case["ebitda_impact"]
    print(f"\n{'─'*40}")
    print("  KEY FINDINGS")
    print(f"{'─'*40}")
    print(f"  Annual Cost Savings:    ${ebitda['annual_cost_savings']:>12,.2f}")
    print(f"  EBITDA Margin Expansion: {ebitda['margin_expansion_bps']:>10.0f} bps")
    print(f"  New EBITDA Margin:       {ebitda['new_margin']:>10.1%}")
    print(f"  Payback Period:          {ebitda['payback_months']:>10.1f} months")
    print(f"  Year 1 ROI:              {ebitda['roi_year1']:>10.1f}%")
    print(f"  Valuation Uplift (10x):  ${ebitda['valuation_uplift']:>12,.2f}")
    print(f"  Migration Cost:          ${ebitda['migration_cost']:>12,.2f}")
    print(f"\n  Tear sheet: {html_path}")
    if png_path:
        print(f"  PNG export: {png_path}")
    print(f"  Output dir: {output_dir}/")

    return case


def main():
    parser = argparse.ArgumentParser(
        description="Inversion Capital On-Chain Diligence Pipeline"
    )
    parser.add_argument(
        "--mode", choices=["protocol", "business"], required=True,
        help="'protocol' for screening, 'business' for full diligence",
    )

    # Protocol screening args
    parser.add_argument(
        "--slugs", type=str, default="",
        help="Comma-separated protocol slugs (for protocol mode)",
    )

    # Business diligence args
    parser.add_argument("--name", type=str, default="TargetCo")
    parser.add_argument("--sector", type=str, default="financial_services")
    parser.add_argument("--revenue", type=float, default=5_000_000)
    parser.add_argument("--ebitda-margin", type=float, default=0.15)
    parser.add_argument("--monthly-tx", type=int, default=50_000)
    parser.add_argument("--avg-tx-value", type=float, default=50)
    parser.add_argument(
        "--payment-method", type=str, default="credit_card",
        choices=["credit_card", "wire_transfer", "ach", "cross_border"],
    )
    parser.add_argument(
        "--target-chain", type=str, default="polygon_usdc",
        choices=list(__import__("config").WEB3_COSTS.keys()),
    )

    args = parser.parse_args()

    if args.mode == "protocol":
        if not args.slugs:
            parser.error("--slugs is required for protocol mode")
        slugs = [s.strip() for s in args.slugs.split(",")]
        run_protocol_screening(slugs)

    elif args.mode == "business":
        profile = {
            "name": args.name,
            "sector": args.sector,
            "annual_revenue": args.revenue,
            "ebitda_margin": args.ebitda_margin,
            "monthly_transactions": args.monthly_tx,
            "avg_transaction_value": args.avg_tx_value,
            "current_payment_method": args.payment_method,
            "target_chain": args.target_chain,
        }
        run_business_diligence(profile)


if __name__ == "__main__":
    main()
