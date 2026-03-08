"""
PE feasibility analysis: Web2 vs Web3 cost comparison, EBITDA impact, sensitivity analysis.
"""

import pandas as pd

from config import WEB2_COSTS, WEB3_COSTS, MIGRATION_COSTS, CONVERSION_TIERS, DEFAULT_ADOPTION_SCHEDULE


class FeasibilityAnalyzer:
    def __init__(self, company_profile):
        """
        company_profile dict keys:
            name, sector, annual_revenue, ebitda_margin,
            monthly_transactions, avg_transaction_value,
            current_payment_method, target_chain
        """
        self.profile = company_profile

    def _monthly_web2_cost(self):
        method = self.profile["current_payment_method"]
        costs = WEB2_COSTS.get(method, WEB2_COSTS["credit_card"])
        monthly_tx = self.profile["monthly_transactions"]
        avg_value = self.profile["avg_transaction_value"]

        processing = monthly_tx * avg_value * costs["processing_rate"]
        per_tx = monthly_tx * costs["per_tx_fee"]
        platform = costs["monthly_platform_fee"]
        chargebacks = monthly_tx * costs["chargeback_rate"] * costs["chargeback_fee"]

        return processing + per_tx + platform + chargebacks

    def _monthly_web3_cost(self):
        chain = self.profile["target_chain"]
        costs = WEB3_COSTS.get(chain, WEB3_COSTS["polygon_usdc"])
        monthly_tx = self.profile["monthly_transactions"]
        avg_value = self.profile["avg_transaction_value"]

        tier = self.profile.get("conversion_tier")
        if tier and tier in CONVERSION_TIERS:
            conversion_rate = CONVERSION_TIERS[tier]["rate"]
        else:
            conversion_rate = costs["treasury_conversion_rate"]

        gas = monthly_tx * costs["avg_gas_fee"]
        onramp = monthly_tx * avg_value * conversion_rate
        infra = costs["monthly_infra"]

        return gas + onramp + infra

    def _get_adoption_schedule(self, months=12):
        """Per-month adoption fractions. Returns [1.0]*months when curve is off."""
        if not self.profile.get("use_adoption_curve", False):
            return [1.0] * months

        sched = DEFAULT_ADOPTION_SCHEDULE
        m1 = sched["month_1_pct"]
        ramp_end = sched["ramp_end_month"]
        ramp_pct = sched["ramp_end_pct"]
        steady = sched["steady_state_pct"]

        result = []
        for m in range(1, months + 1):
            if m == 1:
                result.append(m1)
            elif m <= ramp_end:
                # linear ramp from m1 at month 1 to ramp_pct at ramp_end
                result.append(m1 + (ramp_pct - m1) * (m - 1) / (ramp_end - 1))
            else:
                result.append(steady)
        return result

    def calculate_cost_comparison(self, months=12):
        """12-month Web2 vs Web3 cost projection DataFrame."""
        web2_monthly = self._monthly_web2_cost()
        web3_full = self._monthly_web3_cost()
        adoption = self._get_adoption_schedule(months)
        use_curve = self.profile.get("use_adoption_curve", False)

        chain = self.profile["target_chain"]
        chain_costs = WEB3_COSTS.get(chain, WEB3_COSTS["polygon_usdc"])
        migration_total = sum([
            MIGRATION_COSTS["assessment_30d"],
            MIGRATION_COSTS["infrastructure_build_60d"],
            MIGRATION_COSTS["migration_cutover_30d"],
            MIGRATION_COSTS["compliance_legal"],
            MIGRATION_COSTS["staff_training"],
            chain_costs["smart_contract_audit"],
        ])

        rows = []
        web2_cumulative = 0
        web3_cumulative = migration_total  # upfront migration cost

        for i, month in enumerate(range(1, months + 1)):
            adopt_pct = adoption[i]
            blended = web3_full * adopt_pct + web2_monthly * (1 - adopt_pct)

            web2_cumulative += web2_monthly
            web3_cumulative += blended

            row = {
                "month": month,
                "web2_monthly": round(web2_monthly, 2),
                "web3_monthly": round(blended, 2),
                "web2_cumulative": round(web2_cumulative, 2),
                "web3_cumulative": round(web3_cumulative, 2),
                "monthly_savings": round(web2_monthly - blended, 2),
                "cumulative_savings": round(web2_cumulative - web3_cumulative, 2),
            }
            if use_curve:
                row["adoption_pct"] = round(adopt_pct, 4)
            rows.append(row)

        return pd.DataFrame(rows)

    def calculate_ebitda_impact(self):
        """EBITDA margin expansion, valuation uplift, payback period."""
        web2_monthly = self._monthly_web2_cost()
        web3_full = self._monthly_web3_cost()
        adoption = self._get_adoption_schedule(12)

        web2_annual = web2_monthly * 12
        web3_annual = sum(
            web3_full * a + web2_monthly * (1 - a) for a in adoption
        )
        annual_savings = min(web2_annual - web3_annual, web2_annual)

        revenue = self.profile["annual_revenue"]
        current_margin = self.profile["ebitda_margin"]
        current_ebitda = revenue * current_margin

        new_ebitda = current_ebitda + annual_savings
        new_margin = new_ebitda / revenue if revenue else 0
        margin_expansion_bps = (new_margin - current_margin) * 10000

        # PE valuation: typical 8-12x EBITDA multiple
        ev_multiple = 8
        valuation_uplift = annual_savings * ev_multiple

        # Payback period
        chain = self.profile["target_chain"]
        chain_costs = WEB3_COSTS.get(chain, WEB3_COSTS["polygon_usdc"])
        migration_total = sum([
            MIGRATION_COSTS["assessment_30d"],
            MIGRATION_COSTS["infrastructure_build_60d"],
            MIGRATION_COSTS["migration_cutover_30d"],
            MIGRATION_COSTS["compliance_legal"],
            MIGRATION_COSTS["staff_training"],
            chain_costs["smart_contract_audit"],
        ])

        monthly_savings = (web2_annual - web3_annual) / 12
        payback_months = migration_total / monthly_savings if monthly_savings > 0 else float("inf")

        return {
            "current_ebitda": round(current_ebitda, 2),
            "new_ebitda": round(new_ebitda, 2),
            "annual_cost_savings": round(annual_savings, 2),
            "current_margin": round(current_margin, 4),
            "new_margin": round(new_margin, 4),
            "margin_expansion_bps": round(margin_expansion_bps, 1),
            "ev_multiple": ev_multiple,
            "valuation_uplift": round(valuation_uplift, 2),
            "migration_cost": round(migration_total, 2),
            "payback_months": round(payback_months, 1),
            "roi_year1": round((annual_savings - migration_total) / migration_total * 100, 1)
            if migration_total > 0 else 0,
        }

    def run_sensitivity_analysis(self):
        """4x4 matrix of fee volatility x growth scenarios."""
        fee_multipliers = [0.5, 1.0, 1.5, 2.0]
        growth_rates = [0.0, 0.10, 0.25, 0.50]

        base_web2 = self._monthly_web2_cost()
        base_web3 = self._monthly_web3_cost()
        adoption = self._get_adoption_schedule(12)

        rows = []
        for fee_mult in fee_multipliers:
            for growth in growth_rates:
                adjusted_web3 = base_web3 * fee_mult
                adjusted_web2 = base_web2 * (1 + growth)  # growth increases tx volume -> costs
                annual_web3 = sum(
                    adjusted_web3 * a + adjusted_web2 * (1 - a) for a in adoption
                )
                annual_web2 = adjusted_web2 * 12
                annual_savings = annual_web2 - annual_web3

                rows.append({
                    "fee_multiplier": fee_mult,
                    "growth_rate": growth,
                    "annual_web2_cost": round(annual_web2, 2),
                    "annual_web3_cost": round(annual_web3, 2),
                    "annual_savings": round(annual_savings, 2),
                    "savings_positive": annual_savings > 0,
                })

        return pd.DataFrame(rows)
