"""
trial-balance-auditor: audit.py
Parses a CSV trial balance, auto-detects debit/credit columns,
computes totals, checks balance, and flags data quality issues.
Outputs a structured JSON audit report.
"""

import sys
import json
import argparse
import math
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print(json.dumps({"error": "pandas is required. Run: pip install pandas"}))
    sys.exit(1)


# ─── Column name recognition ────────────────────────────────────────────────

# Strong keywords → confident match, no warning
DEBIT_STRONG   = ["debit", "dr.", "dr ", "借方", "debits"]
CREDIT_STRONG  = ["credit", "cr.", "cr ", "贷方", "credits"]

# Weak keywords → match but emit a warning for user confirmation
DEBIT_WEAK     = ["charges", "outflow", "expense", "payment out"]
CREDIT_WEAK    = ["payments", "inflow", "income", "receipt"]

def classify_columns(columns: list[str]) -> dict:
    """
    Classify each column as debit (strong), debit (weak),
    credit (strong), credit (weak), or unmatched.
    Returns a dict with keys: debit_strong, debit_weak, credit_strong, credit_weak.
    """
    result = {"debit_strong": [], "debit_weak": [],
              "credit_strong": [], "credit_weak": []}

    for col in columns:
        cl = col.strip().lower()
        if any(kw in cl for kw in DEBIT_STRONG):
            result["debit_strong"].append(col)
        elif any(kw in cl for kw in DEBIT_WEAK):
            result["debit_weak"].append(col)
        elif any(kw in cl for kw in CREDIT_STRONG):
            result["credit_strong"].append(col)
        elif any(kw in cl for kw in CREDIT_WEAK):
            result["credit_weak"].append(col)

    return result


# ─── Anomaly detection ───────────────────────────────────────────────────────

def detect_anomalies(series: pd.Series, col_name: str, threshold_z: float = 3.0) -> list[dict]:
    """Flag negative values and statistical outliers (z-score > threshold)."""
    issues = []

    # Negative values
    neg_idx = series[series < 0].index.tolist()
    for i in neg_idx:
        issues.append({
            "row": int(i) + 2,          # +2: 1-based + header row
            "column": col_name,
            "type": "negative_value",
            "value": float(series[i]),
        })

    # Outliers via z-score (only if enough data points)
    clean = series.dropna()
    if len(clean) >= 4:
        mean = clean.mean()
        std  = clean.std()
        if std > 0:
            for i, val in clean.items():
                z = abs((val - mean) / std)
                if z > threshold_z and i not in neg_idx:
                    issues.append({
                        "row": int(i) + 2,
                        "column": col_name,
                        "type": "statistical_outlier",
                        "value": float(val),
                        "z_score": round(float(z), 2),
                    })

    return issues


# ─── Main audit logic ────────────────────────────────────────────────────────

def audit(csv_path: str, threshold_z: float = 3.0) -> dict:
    path = Path(csv_path)

    # ── 1. Load file ──
    if not path.exists():
        return {"error": f"File not found: {csv_path}"}
    if path.suffix.lower() != ".csv":
        return {"error": f"Expected a .csv file, got: {path.suffix}"}

    try:
        df = pd.read_csv(path)
    except Exception as e:
        return {"error": f"Failed to read CSV: {e}"}

    if df.empty:
        return {"error": "CSV file is empty."}

    columns = df.columns.tolist()
    warnings = []

    # ── 2. Classify columns ──
    classified = classify_columns(columns)
    debit_cols  = classified["debit_strong"] + classified["debit_weak"]
    credit_cols = classified["credit_strong"] + classified["credit_weak"]

    # Warn on weak matches
    if classified["debit_weak"]:
        warnings.append({
            "type": "ambiguous_debit_columns",
            "columns": classified["debit_weak"],
            "message": (
                f"Columns {classified['debit_weak']} were assumed to be Debit "
                f"based on weak keyword match. Please verify this is correct."
            ),
        })
    if classified["credit_weak"]:
        warnings.append({
            "type": "ambiguous_credit_columns",
            "columns": classified["credit_weak"],
            "message": (
                f"Columns {classified['credit_weak']} were assumed to be Credit "
                f"based on weak keyword match. Please verify this is correct."
            ),
        })
    # Warn if multiple columns are being merged
    if len(debit_cols) > 1:
        warnings.append({
            "type": "multiple_debit_columns",
            "columns": debit_cols,
            "message": (
                f"Multiple Debit columns detected: {debit_cols}. "
                f"Their values will be summed. Please confirm this is intended."
            ),
        })
    if len(credit_cols) > 1:
        warnings.append({
            "type": "multiple_credit_columns",
            "columns": credit_cols,
            "message": (
                f"Multiple Credit columns detected: {credit_cols}. "
                f"Their values will be summed. Please confirm this is intended."
            ),
        })

    if not debit_cols:
        return {
            "error": "Could not identify any Debit column.",
            "hint": f"Columns found: {columns}. "
                    f"Expected names containing: {DEBIT_STRONG + DEBIT_WEAK}",
        }
    if not credit_cols:
        return {
            "error": "Could not identify any Credit column.",
            "hint": f"Columns found: {columns}. "
                    f"Expected names containing: {CREDIT_STRONG + CREDIT_WEAK}",
        }

    # ── 3. Coerce to numeric ──
    for col in debit_cols + credit_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # ── 4. Missing value detection ──
    missing = []
    for col in debit_cols + credit_cols:
        null_rows = df[df[col].isna()].index.tolist()
        for i in null_rows:
            missing.append({
                "row": int(i) + 2,
                "column": col,
                "type": "missing_value",
            })

    # ── 5. Compute totals (sum across all matched columns) ──
    total_debit  = float(df[debit_cols].sum(skipna=True).sum())
    total_credit = float(df[credit_cols].sum(skipna=True).sum())
    difference   = round(total_debit - total_credit, 6)
    is_balanced  = math.isclose(total_debit, total_credit, rel_tol=1e-6)

    # ── 6. Anomaly detection ──
    anomalies = []
    for col in debit_cols + credit_cols:
        anomalies += detect_anomalies(df[col], col, threshold_z)

    # ── 7. Summary counts ──
    total_rows     = len(df)
    missing_count  = len(missing)
    anomaly_count  = len(anomalies)
    warning_count  = len(warnings)
    overall_status = "PASS" if (is_balanced and missing_count == 0 and anomaly_count == 0) else "FAIL"

    return {
        "file": str(path.resolve()),
        "total_rows": total_rows,
        "detected_columns": {
            "debit":  debit_cols,
            "credit": credit_cols,
        },
        "summary": {
            "total_debit":   round(total_debit,  2),
            "total_credit":  round(total_credit, 2),
            "difference":    round(difference,   2),
            "is_balanced":   is_balanced,
            "missing_count": missing_count,
            "anomaly_count": anomaly_count,
            "warning_count": warning_count,
            "overall_status": overall_status,
        },
        "warnings":      warnings,
        "missing_values": missing,
        "anomalies":     anomalies,
    }


# ─── CLI entry point ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Audit a CSV trial balance and output a JSON report."
    )
    parser.add_argument("csv_file", help="Path to the CSV trial balance file")
    parser.add_argument(
        "--z-threshold", type=float, default=3.0,
        help="Z-score threshold for outlier detection (default: 3.0)"
    )
    args = parser.parse_args()

    result = audit(args.csv_file, threshold_z=args.z_threshold)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
