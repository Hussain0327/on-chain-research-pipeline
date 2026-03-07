"""
Investment Committee tear sheet generator using Plotly.
2x2 grid: cost comparison, EBITDA waterfall, sensitivity heatmap, chain health trend.
"""

import os

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


# Dark theme colors
BG_COLOR = "#1a1a2e"
PAPER_COLOR = "#16213e"
TEXT_COLOR = "#e0e0e0"
GREEN = "#00d4aa"
RED = "#ff4757"
BLUE = "#0984e3"
ORANGE = "#fdcb6e"
GRID_COLOR = "#2d3436"


def generate_tearsheet(business_case, output_dir):
    """
    Generate a 2x2 tear sheet from a business case dict.
    Exports HTML + PNG.
    """
    company = business_case["company_profile"]
    cost_df = business_case["cost_comparison"]
    ebitda = business_case["ebitda_impact"]
    sensitivity_df = business_case["sensitivity"]
    chain_df = business_case["chain_analysis"]

    title = f"Investment Tear Sheet: {company['name']}"

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            "12-Month Cost Comparison (Web2 vs Web3)",
            "EBITDA Impact Waterfall",
            "Sensitivity Analysis (Annual Savings $)",
            "Chain Ecosystem Health",
        ],
        vertical_spacing=0.12,
        horizontal_spacing=0.1,
    )

    # --- Panel 1: Cost comparison line chart ---
    fig.add_trace(
        go.Scatter(
            x=cost_df["month"], y=cost_df["web2_cumulative"],
            name="Web2 Cumulative", line=dict(color=RED, width=2),
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=cost_df["month"], y=cost_df["web3_cumulative"],
            name="Web3 Cumulative", line=dict(color=GREEN, width=2),
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Bar(
            x=cost_df["month"], y=cost_df["monthly_savings"],
            name="Monthly Savings", marker_color=BLUE, opacity=0.5,
        ),
        row=1, col=1,
    )

    # --- Panel 2: EBITDA waterfall ---
    waterfall_categories = ["Current EBITDA", "Cost Savings", "Migration Cost", "New EBITDA"]
    waterfall_values = [
        ebitda["current_ebitda"],
        ebitda["annual_cost_savings"],
        -ebitda["migration_cost"],
        ebitda["new_ebitda"],
    ]
    waterfall_measure = ["absolute", "relative", "relative", "total"]

    fig.add_trace(
        go.Waterfall(
            x=waterfall_categories,
            y=waterfall_values,
            measure=waterfall_measure,
            connector=dict(line=dict(color=GRID_COLOR)),
            increasing=dict(marker=dict(color=GREEN)),
            decreasing=dict(marker=dict(color=RED)),
            totals=dict(marker=dict(color=BLUE)),
            name="EBITDA",
        ),
        row=1, col=2,
    )

    # --- Panel 3: Sensitivity heatmap ---
    fee_mults = sorted(sensitivity_df["fee_multiplier"].unique())
    growth_rates = sorted(sensitivity_df["growth_rate"].unique())

    z_matrix = []
    for fm in fee_mults:
        row = []
        for gr in growth_rates:
            val = sensitivity_df[
                (sensitivity_df["fee_multiplier"] == fm) &
                (sensitivity_df["growth_rate"] == gr)
            ]["annual_savings"].values
            row.append(val[0] if len(val) > 0 else 0)
        z_matrix.append(row)

    fig.add_trace(
        go.Heatmap(
            z=z_matrix,
            x=[f"{g:.0%}" for g in growth_rates],
            y=[f"{f}x" for f in fee_mults],
            colorscale=[[0, RED], [0.5, ORANGE], [1, GREEN]],
            colorbar=dict(title="Savings ($)", x=1.02, len=0.4, y=0.2),
            name="Sensitivity",
        ),
        row=2, col=1,
    )

    # --- Panel 4: Chain ecosystem health ---
    if not chain_df.empty:
        fig.add_trace(
            go.Bar(
                x=chain_df["chain"],
                y=chain_df["tvl"],
                name="TVL ($)",
                marker_color=BLUE,
            ),
            row=2, col=2,
        )
        fig.add_trace(
            go.Bar(
                x=chain_df["chain"],
                y=chain_df["stablecoin_supply"],
                name="Stablecoin Supply ($)",
                marker_color=GREEN,
            ),
            row=2, col=2,
        )

    # --- Layout ---
    fig.update_layout(
        title=dict(text=title, font=dict(size=20, color=TEXT_COLOR)),
        paper_bgcolor=PAPER_COLOR,
        plot_bgcolor=BG_COLOR,
        font=dict(color=TEXT_COLOR, size=11),
        showlegend=True,
        legend=dict(
            bgcolor="rgba(0,0,0,0.3)",
            font=dict(color=TEXT_COLOR, size=9),
            x=0.5, y=-0.08, xanchor="center",
            orientation="h",
        ),
        height=900,
        width=1400,
        barmode="group",
    )

    # Style all axes
    for i in range(1, 5):
        row = (i - 1) // 2 + 1
        col = (i - 1) % 2 + 1
        fig.update_xaxes(gridcolor=GRID_COLOR, row=row, col=col)
        fig.update_yaxes(gridcolor=GRID_COLOR, row=row, col=col)

    # Add key metrics annotation
    metrics_text = (
        f"Margin Expansion: {ebitda['margin_expansion_bps']:.0f} bps | "
        f"Payback: {ebitda['payback_months']:.1f} mo | "
        f"Year 1 ROI: {ebitda['roi_year1']:.0f}% | "
        f"Valuation Uplift: ${ebitda['valuation_uplift']:,.0f}"
    )
    fig.add_annotation(
        text=metrics_text,
        xref="paper", yref="paper",
        x=0.5, y=1.06, showarrow=False,
        font=dict(size=12, color=GREEN),
        xanchor="center",
    )

    # Export
    os.makedirs(output_dir, exist_ok=True)
    html_path = os.path.join(output_dir, "tearsheet.html")
    fig.write_html(html_path)

    png_path = os.path.join(output_dir, "tearsheet.png")
    try:
        fig.write_image(png_path, scale=2)
    except Exception:
        png_path = None  # kaleido not available

    return html_path, png_path
