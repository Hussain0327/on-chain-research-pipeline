"""
Unit tests for transform logic — pure math, no API calls.
"""

import pytest
import pandas as pd

from transform.pe_feasibility import FeasibilityAnalyzer
from transform.screening import screen_protocol_as_target


@pytest.fixture
def sample_profile():
    return {
        "name": "TestCo",
        "sector": "financial_services",
        "annual_revenue": 3_000_000,
        "ebitda_margin": 0.15,
        "monthly_transactions": 50_000,
        "avg_transaction_value": 60,
        "current_payment_method": "credit_card",
        "target_chain": "avalanche_usdc",
    }


@pytest.fixture
def analyzer(sample_profile):
    return FeasibilityAnalyzer(sample_profile)


class TestFeasibilityAnalyzer:
    def test_monthly_web2_cost_positive(self, analyzer):
        cost = analyzer._monthly_web2_cost()
        assert cost > 0

    def test_monthly_web3_cost_positive(self, analyzer):
        cost = analyzer._monthly_web3_cost()
        assert cost > 0

    def test_web3_cheaper_than_web2(self, analyzer):
        """Core thesis: on-chain payments should be cheaper."""
        web2 = analyzer._monthly_web2_cost()
        web3 = analyzer._monthly_web3_cost()
        assert web3 < web2

    def test_cost_comparison_shape(self, analyzer):
        df = analyzer.calculate_cost_comparison(months=12)
        assert len(df) == 12
        assert "web2_monthly" in df.columns
        assert "web3_monthly" in df.columns
        assert "cumulative_savings" in df.columns

    def test_cost_comparison_cumulative_increasing(self, analyzer):
        df = analyzer.calculate_cost_comparison(months=12)
        assert df["web2_cumulative"].is_monotonic_increasing
        assert df["web3_cumulative"].is_monotonic_increasing

    def test_ebitda_impact_keys(self, analyzer):
        result = analyzer.calculate_ebitda_impact()
        expected_keys = [
            "current_ebitda", "new_ebitda", "annual_cost_savings",
            "current_margin", "new_margin", "margin_expansion_bps",
            "ev_multiple", "valuation_uplift", "migration_cost",
            "payback_months", "roi_year1",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    def test_ebitda_margin_expands(self, analyzer):
        result = analyzer.calculate_ebitda_impact()
        assert result["new_margin"] > result["current_margin"]
        assert result["margin_expansion_bps"] > 0

    def test_payback_period_reasonable(self, analyzer):
        result = analyzer.calculate_ebitda_impact()
        assert 0 < result["payback_months"] < 120  # less than 10 years

    def test_sensitivity_shape(self, analyzer):
        df = analyzer.run_sensitivity_analysis()
        assert len(df) == 16  # 4x4 matrix
        assert "fee_multiplier" in df.columns
        assert "growth_rate" in df.columns
        assert "annual_savings" in df.columns

    def test_sensitivity_higher_growth_increases_web2_cost(self, analyzer):
        df = analyzer.run_sensitivity_analysis()
        at_1x_fee = df[df["fee_multiplier"] == 1.0].sort_values("growth_rate")
        assert at_1x_fee["annual_web2_cost"].is_monotonic_increasing


class TestSavingsGuardrails:
    """Regression tests: savings must never exceed Web2 annual costs."""

    @pytest.mark.parametrize("payment_method", ["credit_card", "wire_transfer", "cross_border"])
    def test_savings_never_exceed_web2_annual(self, payment_method):
        profile = {
            "name": "GuardTest",
            "sector": "test",
            "annual_revenue": 5_000_000,
            "ebitda_margin": 0.15,
            "monthly_transactions": 50_000,
            "avg_transaction_value": 500,
            "current_payment_method": payment_method,
            "target_chain": "avalanche_usdc",
            "use_adoption_curve": True,
        }
        fa = FeasibilityAnalyzer(profile)
        ebitda = fa.calculate_ebitda_impact()
        web2_annual = fa._monthly_web2_cost() * 12
        assert ebitda["annual_cost_savings"] <= web2_annual

    def test_savings_with_adoption_curve_less_than_without(self):
        base = {
            "name": "CurveTest",
            "sector": "test",
            "annual_revenue": 5_000_000,
            "ebitda_margin": 0.15,
            "monthly_transactions": 50_000,
            "avg_transaction_value": 200,
            "current_payment_method": "credit_card",
            "target_chain": "polygon_usdc",
        }
        profile_off = {**base, "use_adoption_curve": False}
        profile_on = {**base, "use_adoption_curve": True}

        savings_off = FeasibilityAnalyzer(profile_off).calculate_ebitda_impact()["annual_cost_savings"]
        savings_on = FeasibilityAnalyzer(profile_on).calculate_ebitda_impact()["annual_cost_savings"]
        assert savings_on < savings_off

    def test_freight_broker_savings_reasonable(self):
        profile = {
            "name": "Freight Broker",
            "sector": "logistics",
            "annual_revenue": 8_000_000,
            "ebitda_margin": 0.10,
            "monthly_transactions": 25_000,
            "avg_transaction_value": 2_000,
            "current_payment_method": "wire_transfer",
            "target_chain": "avalanche_usdc",
            "use_adoption_curve": True,
        }
        fa = FeasibilityAnalyzer(profile)
        ebitda = fa.calculate_ebitda_impact()
        assert ebitda["margin_expansion_bps"] < 5000


class TestProtocolScreening:
    def test_strong_protocol_scores_high(self):
        snapshot = {
            "slug": "aave-v3",
            "name": "Aave V3",
            "total_tvl": 5_000_000_000,
            "daily_fees": 200_000,
            "daily_revenue": 200_000,
            "daily_volume": 500_000_000,
            "chains": ["Ethereum", "Polygon", "Arbitrum", "Avalanche", "Optimism",
                        "Base", "BSC", "Fantom", "Harmony", "Metis"],
            "mcap_tvl_ratio": 0.3,
        }
        result = screen_protocol_as_target(snapshot)
        assert result["composite_score"] >= 70
        assert result["recommendation"] in ("Strong Buy", "Buy")

    def test_weak_protocol_scores_low(self):
        snapshot = {
            "slug": "tiny-dex",
            "name": "Tiny DEX",
            "total_tvl": 100_000,
            "daily_fees": 50,
            "daily_revenue": 50,
            "daily_volume": 10_000,
            "chains": ["Ethereum"],
            "mcap_tvl_ratio": 8.0,
        }
        result = screen_protocol_as_target(snapshot)
        assert result["composite_score"] < 30
        assert result["recommendation"] == "Pass"

    def test_screening_returns_all_dimensions(self):
        snapshot = {
            "slug": "test",
            "name": "Test",
            "total_tvl": 50_000_000,
            "daily_fees": 5_000,
            "chains": ["Ethereum", "Polygon"],
            "mcap_tvl_ratio": 1.5,
            "daily_volume": 10_000_000,
        }
        result = screen_protocol_as_target(snapshot)
        expected_dims = [
            "tvl_strength", "revenue_quality", "multi_chain",
            "capital_efficiency", "volume_activity",
        ]
        for dim in expected_dims:
            assert dim in result["scores"]
            assert 0 <= result["scores"][dim] <= 100
