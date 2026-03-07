"""
CSV export functions for pipeline outputs.
"""

import os

import pandas as pd


def _ensure_dir(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def export_cost_comparison(df, output_dir):
    path = os.path.join(output_dir, "cost_comparison.csv")
    _ensure_dir(path)
    df.to_csv(path, index=False)
    return path


def export_sensitivity(df, output_dir):
    path = os.path.join(output_dir, "sensitivity_analysis.csv")
    _ensure_dir(path)
    df.to_csv(path, index=False)
    return path


def export_chain_analysis(df, output_dir):
    path = os.path.join(output_dir, "chain_analysis.csv")
    _ensure_dir(path)
    df.to_csv(path, index=False)
    return path


def export_screening_results(results, output_dir):
    path = os.path.join(output_dir, "screening_results.csv")
    _ensure_dir(path)

    rows = []
    for r in results:
        row = {
            "slug": r["slug"],
            "name": r["name"],
            "composite_score": r["composite_score"],
            "recommendation": r["recommendation"],
        }
        row.update(r.get("scores", {}))
        rows.append(row)

    pd.DataFrame(rows).to_csv(path, index=False)
    return path
