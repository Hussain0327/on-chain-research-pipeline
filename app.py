"""
Inversion Capital On-Chain Diligence Pipeline — Streamlit App
"""

import io
import zipfile
from datetime import datetime

import requests
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from config import WEB2_COSTS, WEB3_COSTS, CONVERSION_TIERS
from extract.defillama_client import DeFiLlamaClient
from transform.pe_feasibility import FeasibilityAnalyzer
from transform.screening import (
    generate_traditional_business_case,
    screen_multiple_protocols,
)
from load.tearsheet import generate_tearsheet

# ---------------------------------------------------------------------------
# Brand palette (Inversion Capital)
# ---------------------------------------------------------------------------
DARK_GREEN = "#2D4A3E"
CREAM = "#F5F0E8"
GOLD = "#8B7D3C"
RED = "#C45B4A"
TEXT_DARK = "#1a1a1a"
TEXT_LIGHT = "#F5F0E8"
GRID = "#D5CFC4"
GOLD_LIGHT = "#B8A960"

# ---------------------------------------------------------------------------
# Friendly labels
# ---------------------------------------------------------------------------
PAYMENT_LABELS = {
    "credit_card": "Credit Card (2.9% + $0.30)",
    "wire_transfer": "Wire Transfer ($25/tx)",
    "ach": "ACH (0.8% + $0.25)",
    "cross_border": "Cross-Border (3.5% + $15/tx)",
}

CHAIN_LABELS = {
    "ethereum_usdc": "USDC on Ethereum (~$3.50/tx)",
    "polygon_usdc": "USDC on Polygon (~$0.01/tx)",
    "arbitrum_usdc": "USDC on Arbitrum (~$0.10/tx)",
    "avalanche_usdc": "USDC on Avalanche (~$0.05/tx)",
    "solana_usdc": "USDC on Solana (~$0.005/tx)",
    "base_usdc": "USDC on Base (~$0.02/tx)",
}

TIER_LABELS = {k: v["label"] for k, v in CONVERSION_TIERS.items()}

# ---------------------------------------------------------------------------
# Sector archetypes for Market Scanner
# ---------------------------------------------------------------------------
SECTOR_ARCHETYPES = [
    {
        "sector": "Telecom MVNO",
        "monthly_transactions": 100_000,
        "avg_transaction_value": 45,
        "current_payment_method": "credit_card",
        "target_chain": "avalanche_usdc",
    },
    {
        "sector": "Freight Brokerage",
        "monthly_transactions": 25_000,
        "avg_transaction_value": 2_000,
        "current_payment_method": "wire_transfer",
        "target_chain": "avalanche_usdc",
    },
    {
        "sector": "Regional Lending",
        "monthly_transactions": 50_000,
        "avg_transaction_value": 500,
        "current_payment_method": "ach",
        "target_chain": "avalanche_usdc",
    },
    {
        "sector": "Cross-border Payments",
        "monthly_transactions": 30_000,
        "avg_transaction_value": 800,
        "current_payment_method": "cross_border",
        "target_chain": "solana_usdc",
    },
    {
        "sector": "Healthcare Billing",
        "monthly_transactions": 75_000,
        "avg_transaction_value": 150,
        "current_payment_method": "credit_card",
        "target_chain": "base_usdc",
    },
    {
        "sector": "SaaS Platform",
        "monthly_transactions": 40_000,
        "avg_transaction_value": 200,
        "current_payment_method": "credit_card",
        "target_chain": "avalanche_usdc",
    },
]

QUICK_SCENARIOS = {
    "Custom": None,
    "Telecom MVNO ($5M rev, 100K tx/mo, Credit Card)": {
        "name": "Telecom MVNO",
        "sector": "telecom",
        "annual_revenue": 5_000_000,
        "ebitda_margin": 0.12,
        "monthly_transactions": 100_000,
        "avg_transaction_value": 45,
        "current_payment_method": "credit_card",
        "target_chain": "polygon_usdc",
    },
    "Freight Broker ($8M rev, 25K tx/mo, Wire Transfer)": {
        "name": "Freight Broker",
        "sector": "logistics",
        "annual_revenue": 8_000_000,
        "ebitda_margin": 0.10,
        "monthly_transactions": 25_000,
        "avg_transaction_value": 320,
        "current_payment_method": "wire_transfer",
        "target_chain": "avalanche_usdc",
    },
    "Regional Bank ($12M rev, 200K tx/mo, ACH)": {
        "name": "Regional Bank",
        "sector": "financial_services",
        "annual_revenue": 12_000_000,
        "ebitda_margin": 0.20,
        "monthly_transactions": 200_000,
        "avg_transaction_value": 85,
        "current_payment_method": "ach",
        "target_chain": "solana_usdc",
    },
}

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Inversion Capital | On-Chain Diligence",
    page_icon="https://em-content.zobj.net/source/twitter/408/chart-increasing_1f4c8.png",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom CSS — brand overrides
# ---------------------------------------------------------------------------
st.markdown(f"""
<style>
    /* Sidebar: dark green with cream text */
    section[data-testid="stSidebar"] {{
        background-color: {DARK_GREEN} !important;
    }}
    section[data-testid="stSidebar"] * {{
        color: {TEXT_LIGHT} !important;
    }}
    section[data-testid="stSidebar"] hr {{
        border-color: rgba(245, 240, 232, 0.2) !important;
    }}

    /* Metric cards: dark green bg, cream text */
    div[data-testid="stMetric"] {{
        background-color: {DARK_GREEN};
        padding: 16px 20px;
        border-radius: 8px;
    }}
    div[data-testid="stMetric"] label,
    div[data-testid="stMetric"] div[data-testid="stMetricValue"],
    div[data-testid="stMetric"] div[data-testid="stMetricDelta"] {{
        color: {TEXT_LIGHT} !important;
    }}

    /* Buttons: dark green bg, cream text */
    button[kind="primary"] {{
        background-color: {DARK_GREEN} !important;
        color: {TEXT_LIGHT} !important;
        border: none !important;
    }}
    button[kind="primary"]:hover {{
        background-color: #3A5E4F !important;
    }}

    /* Download buttons */
    button[data-testid="stDownloadButton"] > button {{
        background-color: {DARK_GREEN} !important;
        color: {TEXT_LIGHT} !important;
        border: none !important;
    }}

    /* Tab styling */
    button[data-baseweb="tab"] {{
        color: {TEXT_DARK} !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {DARK_GREEN} !important;
        border-bottom-color: {DARK_GREEN} !important;
    }}

    /* Expander headers */
    details summary {{
        color: {DARK_GREEN} !important;
    }}

    /* Input fields on dark green background: white text */
    input, textarea, [data-baseweb="select"] span,
    div[data-baseweb="select"] div {{
        color: {TEXT_LIGHT} !important;
    }}
    /* Dropdown menu items (light bg) keep dark text */
    ul[role="listbox"] li {{
        color: {TEXT_DARK} !important;
    }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        "<h1 style='letter-spacing:0.35em; font-weight:300; "
        f"color:{TEXT_LIGHT}; margin-bottom:0; font-size:28px;'>INVERSION</h1>"
        f"<p style='letter-spacing:0.25em; color:{GOLD_LIGHT}; "
        "margin-top:0; font-size:13px; font-weight:400;'>CAPITAL</p>",
        unsafe_allow_html=True,
    )
    st.caption("On-Chain Diligence Pipeline")
    st.divider()
    st.markdown(
        f"<span style='font-size:12px; color:rgba(245,240,232,0.6);'>"
        f"Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M')}<br>"
        f"Prepared for Investment Committee"
        f"</span>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Plotly layout helper
# ---------------------------------------------------------------------------
def _chart_layout(**overrides):
    base = dict(
        paper_bgcolor=CREAM,
        plot_bgcolor=CREAM,
        font=dict(color=TEXT_DARK, size=12),
        height=420,
        xaxis=dict(gridcolor=GRID),
        yaxis=dict(gridcolor=GRID),
        legend=dict(orientation="h", y=-0.15),
    )
    base.update(overrides)
    return base


@st.cache_data
def _compute_sector_savings(assumed_revenue, assumed_margin):
    sector_rows = []
    for arch in SECTOR_ARCHETYPES:
        profile = {
            "name": arch["sector"],
            "sector": arch["sector"],
            "annual_revenue": assumed_revenue,
            "ebitda_margin": assumed_margin,
            "monthly_transactions": arch["monthly_transactions"],
            "avg_transaction_value": arch["avg_transaction_value"],
            "current_payment_method": arch["current_payment_method"],
            "target_chain": arch["target_chain"],
        }
        profile["use_adoption_curve"] = True
        profile["annual_revenue"] = assumed_revenue
        profile["ebitda_margin"] = assumed_margin
        fa = FeasibilityAnalyzer(profile)
        ebitda = fa.calculate_ebitda_impact()
        web2_annual = fa._monthly_web2_cost() * 12
        web3_annual = web2_annual - ebitda["annual_cost_savings"]
        savings = ebitda["annual_cost_savings"]
        margin_impact_bps = ebitda["margin_expansion_bps"]

        if savings > 500_000:
            thesis = "Strong"
        elif savings > 100_000:
            thesis = "Moderate"
        else:
            thesis = "Weak"

        sector_rows.append({
            "Sector": arch["sector"],
            "Monthly Tx": f"{arch['monthly_transactions']:,}",
            "Avg Tx ($)": f"${arch['avg_transaction_value']:,.0f}",
            "Payment": PAYMENT_LABELS.get(arch["current_payment_method"], arch["current_payment_method"]),
            "Target Chain": CHAIN_LABELS.get(arch["target_chain"], arch["target_chain"]).split("(")[0].strip(),
            "Annual Web2 Cost": web2_annual,
            "Annual Web3 Cost": web3_annual,
            "Annual Savings": savings,
            "Margin Impact (bps)": round(margin_impact_bps, 0),
            "Thesis Strength": thesis,
            "_monthly_tx": arch["monthly_transactions"],
            "_avg_tx": arch["avg_transaction_value"],
            "_payment": arch["current_payment_method"],
            "_chain": arch["target_chain"],
        })

    return pd.DataFrame(sector_rows).sort_values("Annual Savings", ascending=False)


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_business, tab_screening, tab_scanner = st.tabs([
    "Business Diligence", "Protocol Screening", "Market Scanner",
])


# ===========================================================================
# TAB 1: Business Diligence
# ===========================================================================
with tab_business:

    # --- Quick Scenarios ---
    scenario_key = st.selectbox("Quick Scenarios", list(QUICK_SCENARIOS.keys()))
    preset = QUICK_SCENARIOS[scenario_key]

    # --- Input form ---
    col_a, col_b, col_c, col_d = st.columns(4)

    with col_a:
        biz_name = st.text_input("Business Name", value=preset["name"] if preset else "TestCo")
        sector = st.text_input("Sector", value=preset["sector"] if preset else "financial_services")

    with col_b:
        revenue = st.number_input(
            "Annual Revenue ($)",
            min_value=100_000, max_value=500_000_000, step=500_000,
            value=preset["annual_revenue"] if preset else 3_000_000,
        )
        margin_pct = st.slider(
            "EBITDA Margin (%)",
            min_value=5, max_value=40, step=1,
            value=int((preset["ebitda_margin"] if preset else 0.15) * 100),
        )
        margin = margin_pct / 100.0

    with col_c:
        monthly_tx = st.number_input(
            "Monthly Transactions",
            min_value=1_000, max_value=10_000_000, step=5_000,
            value=preset["monthly_transactions"] if preset else 50_000,
        )
        avg_tx = st.number_input(
            "Avg Transaction Value ($)",
            min_value=1.0, max_value=50_000.0, step=5.0,
            value=float(preset["avg_transaction_value"] if preset else 60),
        )

    with col_d:
        payment_keys = list(PAYMENT_LABELS.keys())
        payment_default = (
            payment_keys.index(preset["current_payment_method"])
            if preset else 0
        )
        payment_method = st.selectbox(
            "Payment Method",
            payment_keys,
            index=payment_default,
            format_func=lambda k: PAYMENT_LABELS[k],
        )
        chain_keys = list(CHAIN_LABELS.keys())
        chain_default = (
            chain_keys.index(preset["target_chain"])
            if preset else 3
        )
        target_chain = st.selectbox(
            "Target Chain",
            chain_keys,
            index=chain_default,
            format_func=lambda k: CHAIN_LABELS[k],
        )

    # --- Conversion tier & phased rollout ---
    col_e, col_f = st.columns(2)
    with col_e:
        tier_keys = list(TIER_LABELS.keys())
        conversion_tier = st.selectbox(
            "Conversion Tier",
            tier_keys,
            index=tier_keys.index("blended"),
            format_func=lambda k: TIER_LABELS[k],
        )
    with col_f:
        use_adoption_curve = st.toggle("Phased Rollout", value=False)

    # --- Compare Chains toggle ---
    compare_chains = st.toggle("Compare Chains (side-by-side)")
    compare_chain = None
    if compare_chains:
        remaining = [k for k in chain_keys if k != target_chain]
        compare_chain = st.selectbox(
            "Compare with",
            remaining,
            format_func=lambda k: CHAIN_LABELS[k],
        )

    run_btn = st.button("Run Diligence", type="primary", use_container_width=True)

    # --- Run analysis ---
    if run_btn:
        profile = {
            "name": biz_name,
            "sector": sector,
            "annual_revenue": revenue,
            "ebitda_margin": margin,
            "monthly_transactions": monthly_tx,
            "avg_transaction_value": avg_tx,
            "current_payment_method": payment_method,
            "target_chain": target_chain,
            "conversion_tier": conversion_tier,
            "use_adoption_curve": use_adoption_curve,
        }

        with st.spinner("Fetching on-chain data & running analysis..."):
            try:
                client = DeFiLlamaClient()
                case = generate_traditional_business_case(profile, client)

                compare_case = None
                if compare_chains and compare_chain:
                    profile_b = {**profile, "target_chain": compare_chain}
                    compare_case = generate_traditional_business_case(profile_b, client)
            except (requests.RequestException, Exception):
                st.error("Unable to reach DeFiLlama. Please try again in a few minutes.")
                st.stop()

        ebitda = case["ebitda_impact"]
        cost_df = case["cost_comparison"]
        sens_df = case["sensitivity"]
        chain_df = case["chain_analysis"]

        # ---------------------------------------------------------------
        # Row 1: Metric cards
        # ---------------------------------------------------------------
        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Annual Savings", f"${ebitda['annual_cost_savings']:,.0f}")
        m2.metric("Margin Expansion", f"{ebitda['margin_expansion_bps']:.0f} bps")
        m3.metric("Payback Period", f"{ebitda['payback_months']:.1f} mo")
        m4.metric("Valuation Uplift @8x", f"${ebitda['valuation_uplift']:,.0f}")

        if compare_case:
            st.caption(f"Comparison: {CHAIN_LABELS[compare_chain]}")
            eb = compare_case["ebitda_impact"]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Annual Savings", f"${eb['annual_cost_savings']:,.0f}",
                       delta=f"{eb['annual_cost_savings'] - ebitda['annual_cost_savings']:+,.0f}")
            c2.metric("Margin Expansion", f"{eb['margin_expansion_bps']:.0f} bps",
                       delta=f"{eb['margin_expansion_bps'] - ebitda['margin_expansion_bps']:+.0f}")
            c3.metric("Payback Period", f"{eb['payback_months']:.1f} mo",
                       delta=f"{eb['payback_months'] - ebitda['payback_months']:+.1f}", delta_color="inverse")
            c4.metric("Valuation Uplift @8x", f"${eb['valuation_uplift']:,.0f}",
                       delta=f"{eb['valuation_uplift'] - ebitda['valuation_uplift']:+,.0f}")

        # ---------------------------------------------------------------
        # Row 2: Cost comparison + EBITDA waterfall
        # ---------------------------------------------------------------
        left2, right2 = st.columns(2)

        with left2:
            fig_cost = go.Figure()
            fig_cost.add_trace(go.Scatter(
                x=cost_df["month"], y=cost_df["web2_cumulative"],
                name="Web2 Cumulative", line=dict(color=RED, width=3),
            ))
            fig_cost.add_trace(go.Scatter(
                x=cost_df["month"], y=cost_df["web3_cumulative"],
                name=f"Web3 ({CHAIN_LABELS[target_chain].split('(')[0].strip()})",
                line=dict(color=DARK_GREEN, width=3),
            ))
            fig_cost.add_trace(go.Bar(
                x=cost_df["month"], y=cost_df["monthly_savings"],
                name="Monthly Savings", marker_color=GOLD, opacity=0.5,
            ))
            if compare_case:
                cdf = compare_case["cost_comparison"]
                fig_cost.add_trace(go.Scatter(
                    x=cdf["month"], y=cdf["web3_cumulative"],
                    name=f"Web3 ({CHAIN_LABELS[compare_chain].split('(')[0].strip()})",
                    line=dict(color=GOLD_LIGHT, width=3, dash="dash"),
                ))
            layout_kw = _chart_layout(
                title="12-Month Cumulative Cost Comparison",
                xaxis_title="Month", yaxis_title="Cumulative Cost ($)",
            )
            if use_adoption_curve and "adoption_pct" in cost_df.columns:
                fig_cost.add_trace(go.Scatter(
                    x=cost_df["month"],
                    y=cost_df["adoption_pct"] * 100,
                    name="Adoption %",
                    line=dict(color=GOLD_LIGHT, width=2, dash="dot"),
                    yaxis="y2",
                ))
                layout_kw["yaxis2"] = dict(
                    title="Adoption %",
                    overlaying="y",
                    side="right",
                    range=[0, 100],
                    gridcolor=GRID,
                )
            fig_cost.update_layout(**layout_kw)
            st.plotly_chart(fig_cost, use_container_width=True)

        with right2:
            fig_water = go.Figure(go.Waterfall(
                x=["Current EBITDA", "Cost Savings", "Migration Cost", "New EBITDA"],
                y=[
                    ebitda["current_ebitda"],
                    ebitda["annual_cost_savings"],
                    -ebitda["migration_cost"],
                    ebitda["new_ebitda"],
                ],
                measure=["absolute", "relative", "relative", "total"],
                connector=dict(line=dict(color=GRID)),
                increasing=dict(marker=dict(color=DARK_GREEN)),
                decreasing=dict(marker=dict(color=RED)),
                totals=dict(marker=dict(color=GOLD)),
                textposition="outside",
                text=[
                    f"${ebitda['current_ebitda']:,.0f}",
                    f"+${ebitda['annual_cost_savings']:,.0f}",
                    f"-${ebitda['migration_cost']:,.0f}",
                    f"${ebitda['new_ebitda']:,.0f}",
                ],
                textfont=dict(color=TEXT_DARK),
            ))
            fig_water.update_layout(**_chart_layout(
                title="EBITDA Impact Waterfall",
                showlegend=False,
            ))
            st.plotly_chart(fig_water, use_container_width=True)

        # ---------------------------------------------------------------
        # Row 3: Sensitivity heatmap + Chain health
        # ---------------------------------------------------------------
        left3, right3 = st.columns(2)

        with left3:
            fee_mults = sorted(sens_df["fee_multiplier"].unique())
            growth_rates = sorted(sens_df["growth_rate"].unique())

            z_matrix = []
            text_matrix = []
            for fm in fee_mults:
                z_row, t_row = [], []
                for gr in growth_rates:
                    val = sens_df[
                        (sens_df["fee_multiplier"] == fm) &
                        (sens_df["growth_rate"] == gr)
                    ]["annual_savings"].values
                    v = val[0] if len(val) > 0 else 0
                    z_row.append(v)
                    if abs(v) >= 1_000_000:
                        t_row.append(f"${v / 1_000_000:.1f}M")
                    else:
                        t_row.append(f"${v / 1_000:,.0f}K")
                z_matrix.append(z_row)
                text_matrix.append(t_row)

            fig_heat = go.Figure(go.Heatmap(
                z=z_matrix,
                x=[f"{g:.0%} growth" for g in growth_rates],
                y=[f"{f}x fees" for f in fee_mults],
                text=text_matrix,
                texttemplate="%{text}",
                textfont=dict(size=13, color="white"),
                colorscale=[
                    [0, RED],
                    [0.5, GOLD],
                    [1, DARK_GREEN],
                ],
                colorbar=dict(title="Savings ($)"),
            ))
            fig_heat.update_layout(**_chart_layout(
                title="Sensitivity Analysis (Fee Volatility x Growth)",
                xaxis_title="Revenue Growth Scenario",
                yaxis_title="Gas Fee Multiplier",
            ))
            st.plotly_chart(fig_heat, use_container_width=True)

        with right3:
            if not chain_df.empty:
                fig_chain = go.Figure()
                fig_chain.add_trace(go.Bar(
                    x=chain_df["chain"], y=chain_df["tvl"],
                    name="TVL ($)", marker_color=GOLD,
                ))
                fig_chain.add_trace(go.Bar(
                    x=chain_df["chain"], y=chain_df["stablecoin_supply"],
                    name="Stablecoin Supply ($)", marker_color=DARK_GREEN,
                ))

                target_chain_name = target_chain.replace("_usdc", "").replace("_", " ").title()
                target_row = chain_df[chain_df["chain"].str.lower() == target_chain_name.lower()]
                if not target_row.empty:
                    supply_val = target_row.iloc[0]["stablecoin_supply"]
                    supply_b = supply_val / 1e9
                    annotation_text = (
                        f"{target_chain_name} stablecoin supply: ${supply_b:.1f}B"
                        f" — supports {monthly_tx:,} monthly tx at ${avg_tx:.0f} avg"
                    )
                else:
                    annotation_text = ""

                layout_kw = _chart_layout(
                    title="Chain Ecosystem Health",
                    barmode="group",
                )
                fig_chain.update_layout(**layout_kw)
                if annotation_text:
                    fig_chain.add_annotation(
                        text=annotation_text,
                        xref="paper", yref="paper",
                        x=0.5, y=1.08, showarrow=False,
                        font=dict(size=11, color=DARK_GREEN),
                        xanchor="center",
                    )
                st.plotly_chart(fig_chain, use_container_width=True)

        # ---------------------------------------------------------------
        # Row 4: Expandable data tables
        # ---------------------------------------------------------------
        with st.expander("Cost Comparison Data"):
            st.dataframe(cost_df, use_container_width=True, hide_index=True)

        with st.expander("Sensitivity Matrix"):
            st.dataframe(sens_df, use_container_width=True, hide_index=True)

        with st.expander("Chain Analysis"):
            st.dataframe(chain_df, use_container_width=True, hide_index=True)

        # ---------------------------------------------------------------
        # Row 5: Downloads
        # ---------------------------------------------------------------
        st.divider()
        dl1, dl2 = st.columns(2)

        with dl1:
            import os
            import tempfile
            output_dir = os.path.join(tempfile.gettempdir(), f"inversion_{biz_name}")
            html_path, _ = generate_tearsheet(case, output_dir)
            with open(html_path, "r") as f:
                html_bytes = f.read()
            st.download_button(
                "Download Tear Sheet (HTML)",
                data=html_bytes,
                file_name=f"{biz_name}_tearsheet.html",
                mime="text/html",
                use_container_width=True,
            )

        with dl2:
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("cost_comparison.csv", cost_df.to_csv(index=False))
                zf.writestr("sensitivity_analysis.csv", sens_df.to_csv(index=False))
                zf.writestr("chain_analysis.csv", chain_df.to_csv(index=False))
            zip_buf.seek(0)
            st.download_button(
                "Download All CSVs (ZIP)",
                data=zip_buf.getvalue(),
                file_name=f"{biz_name}_data.zip",
                mime="application/zip",
                use_container_width=True,
            )


# ===========================================================================
# TAB 2: Protocol Screening
# ===========================================================================
with tab_screening:
    st.subheader("Protocol Screening")
    slugs_input = st.text_input(
        "Protocol slugs (comma-separated)",
        value="aave-v3, lido, sky-lending",
    )

    if st.button("Screen Protocols", type="primary"):
        slugs = [s.strip() for s in slugs_input.split(",") if s.strip()]
        with st.spinner(f"Screening {len(slugs)} protocols..."):
            try:
                client = DeFiLlamaClient()
                results = screen_multiple_protocols(slugs, client)
            except (requests.RequestException, Exception):
                st.error("Unable to reach DeFiLlama. Please try again in a few minutes.")
                st.stop()

        rows = []
        for r in results:
            row = {
                "Name": r["name"],
                "Slug": r["slug"],
                "Composite Score": r["composite_score"],
                "Recommendation": r["recommendation"],
            }
            row.update({k.replace("_", " ").title(): round(v, 1) for k, v in r.get("scores", {}).items()})
            rows.append(row)

        df = pd.DataFrame(rows)
        st.dataframe(
            df.style.background_gradient(
                subset=["Composite Score"], cmap="RdYlGn", vmin=0, vmax=100,
            ),
            use_container_width=True,
            hide_index=True,
        )

        for r in results:
            if not r.get("scores"):
                continue
            with st.expander(f"{r['name']} — {r['recommendation']} ({r['composite_score']}/100)"):
                for dim, score in r["scores"].items():
                    label = dim.replace("_", " ").title()
                    st.progress(score / 100, text=f"{label}: {score:.0f}/100")


# ===========================================================================
# TAB 3: Market Scanner
# ===========================================================================
with tab_scanner:

    # -------------------------------------------------------------------
    # Section 1: Savings by Sector
    # -------------------------------------------------------------------
    st.subheader("Savings by Sector")
    st.caption(
        "Estimated annual savings for a typical business in each vertical, "
        "assuming 15% EBITDA margin and $5M annual revenue."
    )

    _assumed_revenue = 5_000_000
    _assumed_margin = 0.15

    sector_df = _compute_sector_savings(_assumed_revenue, _assumed_margin)

    display_cols = [
        "Sector", "Monthly Tx", "Avg Tx ($)", "Payment", "Target Chain",
        "Annual Web2 Cost", "Annual Web3 Cost", "Annual Savings",
        "Margin Impact (bps)", "Thesis Strength",
    ]

    def _color_thesis(val):
        if val == "Strong":
            return f"background-color: {DARK_GREEN}; color: {TEXT_LIGHT};"
        elif val == "Moderate":
            return f"background-color: {GOLD}; color: white;"
        return f"background-color: {RED}; color: white;"

    styled_sector = (
        sector_df[display_cols]
        .style
        .format({
            "Annual Web2 Cost": "${:,.0f}",
            "Annual Web3 Cost": "${:,.0f}",
            "Annual Savings": "${:,.0f}",
            "Margin Impact (bps)": "{:.0f}",
        })
        .map(_color_thesis, subset=["Thesis Strength"])
    )

    st.dataframe(styled_sector, use_container_width=True, hide_index=True)

    st.caption("Select a sector to auto-fill the Business Diligence tab:")
    sector_names = sector_df["Sector"].tolist()
    selected_sector = st.selectbox(
        "Load sector into Business Diligence",
        ["(none)"] + sector_names,
        key="scanner_sector_select",
    )
    if selected_sector != "(none)":
        match = sector_df[sector_df["Sector"] == selected_sector].iloc[0]
        prefill_label = (
            f"{selected_sector} "
            f"(${_assumed_revenue / 1e6:.0f}M rev, "
            f"{match['_monthly_tx']:,} tx/mo, "
            f"{match['_payment'].replace('_', ' ').title()})"
        )
        st.info(
            f"Switch to **Business Diligence** tab and select "
            f"**Quick Scenarios > Custom**, then set:\n\n"
            f"- Monthly Transactions: **{match['_monthly_tx']:,}**\n"
            f"- Avg Transaction Value: **${match['_avg_tx']:,.0f}**\n"
            f"- Payment Method: **{PAYMENT_LABELS.get(match['_payment'], match['_payment'])}**\n"
            f"- Target Chain: **{CHAIN_LABELS.get(match['_chain'], match['_chain'])}**"
        )

    # -------------------------------------------------------------------
    # Section 2: Stablecoin Infrastructure Dashboard
    # -------------------------------------------------------------------
    st.divider()
    st.subheader("Stablecoin Infrastructure Dashboard")

    if st.button("Load Live Data", type="primary", key="scanner_load"):
        with st.spinner("Pulling stablecoin data from DeFiLlama..."):
            try:
                from extract.stablecoin_metrics import StablecoinInfraMetrics
                client = DeFiLlamaClient()
                metrics = StablecoinInfraMetrics(client)

                supply_by_chain = metrics.get_stablecoin_supply_by_chain()

                # Supply trend for USDT (id=1) and USDC (id=2)
                trend_usdt = metrics.get_stablecoin_supply_trend(stablecoin_id=1, days=180)
                trend_usdc = metrics.get_stablecoin_supply_trend(stablecoin_id=2, days=180)
            except (requests.RequestException, Exception):
                st.error("Unable to reach DeFiLlama. Please try again in a few minutes.")
                st.stop()

        # --- Top 5 chains by stablecoin supply ---
        top_chains = ["Ethereum", "Tron", "Arbitrum", "Solana", "Avalanche", "Base"]
        if not supply_by_chain.empty:
            chain_totals = (
                supply_by_chain
                .groupby("chain")["circulating_supply_usd"]
                .sum()
                .sort_values(ascending=False)
                .head(8)
            )

            fig_supply = go.Figure()
            fig_supply.add_trace(go.Bar(
                x=chain_totals.index,
                y=chain_totals.values,
                marker_color=[DARK_GREEN if c in top_chains else GOLD for c in chain_totals.index],
                text=[f"${v / 1e9:.1f}B" for v in chain_totals.values],
                textposition="outside",
                textfont=dict(color=TEXT_DARK),
            ))
            fig_supply.update_layout(**_chart_layout(
                title="Stablecoin Supply by Chain (USDC + USDT)",
                showlegend=False,
                yaxis_title="Supply (USD)",
            ))
            st.plotly_chart(fig_supply, use_container_width=True)

        # --- 6-month supply trend ---
        col_trend1, col_trend2 = st.columns(2)

        with col_trend1:
            if trend_usdt is not None and not trend_usdt.empty:
                fig_usdt = go.Figure()
                fig_usdt.add_trace(go.Scatter(
                    x=trend_usdt["date"],
                    y=trend_usdt["circulating_supply_usd"],
                    fill="tozeroy",
                    line=dict(color=DARK_GREEN, width=2),
                    fillcolor="rgba(45,74,62,0.15)",
                    name="USDT",
                ))
                fig_usdt.update_layout(**_chart_layout(
                    title="USDT Supply Trend (6 months)",
                    showlegend=False,
                    yaxis_title="Circulating Supply (USD)",
                    height=350,
                ))
                st.plotly_chart(fig_usdt, use_container_width=True)

        with col_trend2:
            if trend_usdc is not None and not trend_usdc.empty:
                fig_usdc = go.Figure()
                fig_usdc.add_trace(go.Scatter(
                    x=trend_usdc["date"],
                    y=trend_usdc["circulating_supply_usd"],
                    fill="tozeroy",
                    line=dict(color=GOLD, width=2),
                    fillcolor="rgba(139,125,60,0.15)",
                    name="USDC",
                ))
                fig_usdc.update_layout(**_chart_layout(
                    title="USDC Supply Trend (6 months)",
                    showlegend=False,
                    yaxis_title="Circulating Supply (USD)",
                    height=350,
                ))
                st.plotly_chart(fig_usdc, use_container_width=True)

    # -------------------------------------------------------------------
    # Section 3: Chain Comparison Matrix
    # -------------------------------------------------------------------
    st.divider()
    st.subheader("Chain Comparison Matrix")

    CHAIN_META = {
        "Avalanche": {"key": "avalanche_usdc", "settlement": "~2s"},
        "Solana":    {"key": "solana_usdc",    "settlement": "~0.4s"},
        "Base":      {"key": "base_usdc",      "settlement": "~2s"},
        "Arbitrum":  {"key": "arbitrum_usdc",   "settlement": "~0.3s"},
        "Ethereum":  {"key": "ethereum_usdc",   "settlement": "~12s"},
    }

    if st.button("Load Chain Matrix", type="primary", key="scanner_chain_matrix"):
        with st.spinner("Fetching chain data..."):
            try:
                from extract.stablecoin_metrics import StablecoinInfraMetrics
                client = DeFiLlamaClient()
                metrics = StablecoinInfraMetrics(client)

                all_chains_raw = client.get_chains()
                supply_by_chain = metrics.get_stablecoin_supply_by_chain()

                # 30-day supply growth: compare current supply to supply 30 days ago
                supply_trend_30d = {}
                for chain_name in CHAIN_META:
                    try:
                        chain_stables = client.get_stablecoin_chains()
                        for entry in chain_stables:
                            if entry.get("name") == chain_name:
                                current = entry.get("totalCirculatingUSD", {}).get("peggedUSD", 0)
                                supply_trend_30d[chain_name] = current
                                break
                    except Exception:
                        pass
            except (requests.RequestException, Exception):
                st.error("Unable to reach DeFiLlama. Please try again in a few minutes.")
                st.stop()

        chain_tvl_map = {c.get("name", ""): c for c in all_chains_raw}
        if not supply_by_chain.empty:
            chain_supply_totals = supply_by_chain.groupby("chain")["circulating_supply_usd"].sum().to_dict()
        else:
            chain_supply_totals = {}

        matrix_rows = []
        for chain_name, meta in CHAIN_META.items():
            chain_config = WEB3_COSTS.get(meta["key"], {})
            chain_info = chain_tvl_map.get(chain_name, {})

            matrix_rows.append({
                "Chain": chain_name,
                "Avg Tx Cost": f"${chain_config.get('avg_gas_fee', 0):.3f}",
                "Settlement": meta["settlement"],
                "Stablecoin Supply": chain_supply_totals.get(chain_name, 0),
                "TVL": chain_info.get("tvl", 0),
                "Active Protocols": chain_info.get("protocols", 0),
            })

        matrix_df = pd.DataFrame(matrix_rows)

        st.dataframe(
            matrix_df.style.format({
                "Stablecoin Supply": "${:,.0f}",
                "TVL": "${:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )
