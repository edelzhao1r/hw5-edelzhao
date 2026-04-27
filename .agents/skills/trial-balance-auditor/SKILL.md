---
name: trial-balance-auditor
description: Audits a CSV trial balance by auto-detecting debit and credit columns, computing totals, checking whether the books balance, and flagging data quality issues such as missing values, negative entries, and statistical outliers. Use when the user asks to check, validate, audit, or inspect a trial balance or accounting CSV file.
---

# Trial Balance Auditor

## When to use this skill

Use this skill when the user provides a CSV file containing trial balance data and asks to:
- Check whether debits and credits balance
- Identify missing, negative, or anomalous values
- Audit or validate the data quality of an accounting file
- Get a structured report on the integrity of a trial balance

## When NOT to use this skill

- The file is not a CSV (e.g. Excel `.xlsx`, PDF, or image scans — ask the user to export to CSV first)
- The user wants to fix or transform the data, not just audit it
- The user is asking general accounting questions unrelated to a specific file
- The CSV contains no numeric debit or credit columns

## Expected inputs

- A CSV file with at least one debit column and one credit column
- Column names do not need to follow a fixed format — the script auto-detects them using keyword matching

**Recognized debit column names** (case-insensitive, partial match):
`debit`, `dr.`, `dr `, `debits`

**Recognized credit column names** (case-insensitive, partial match):
`credit`, `cr.`, `cr `, `credits`

**Ambiguous names** (matched with a warning):
- Debit side: `charges`, `outflow`, `expense`, `payment out`
- Credit side: `payments`, `inflow`, `income`, `receipt`

Multiple debit or credit columns are allowed — their values will be summed, with a warning issued for user confirmation.

## Step-by-step instructions

1. Ask the user to provide (or confirm the path to) their CSV trial balance file.
2. Run the audit script:
   ```
   python3 scripts/audit.py <path-to-file.csv>
   ```
   Optionally adjust the outlier sensitivity:
   ```
   python3 scripts/audit.py <path-to-file.csv> --z-threshold 2.5
   ```
3. Parse the JSON output and generate a clear audit report for the user covering:
   - Which columns were identified as debit and credit
   - Total debit, total credit, and the difference
   - Whether the trial balance is balanced (`PASS`) or not (`FAIL`)
   - Any warnings about ambiguous or multiple columns
   - Any rows with missing values, negative entries, or statistical outliers
4. If warnings are present, highlight them and ask the user to confirm whether the column assignments are correct before drawing conclusions.
5. If the overall status is `FAIL`, summarize the specific issues and suggest next steps (e.g. locate the missing entry, investigate the flagged row).

## Expected output format

The script outputs a JSON object with the following structure:

```json
{
  "file": "<resolved file path>",
  "total_rows": 4,
  "detected_columns": {
    "debit": ["Cash Debit", "Accrual Dr."],
    "credit": ["Credit Amount"]
  },
  "summary": {
    "total_debit": 8000.0,
    "total_credit": 8000.0,
    "difference": 0.0,
    "is_balanced": true,
    "missing_count": 0,
    "anomaly_count": 0,
    "warning_count": 0,
    "overall_status": "PASS"
  },
  "warnings": [],
  "missing_values": [],
  "anomalies": []
}
```

Present this to the user as a readable narrative report, not raw JSON.

## Limitations and important checks

- **Column detection is heuristic.** If column names are highly unconventional, the script may fail to detect them and will return an error with the full column list for reference.
- **Outlier detection requires at least 4 rows** of numeric data per column; smaller files will skip z-score analysis.
- **Negative values are always flagged.** In standard double-entry bookkeeping, negative debit or credit entries are unusual and warrant review — but they are not always errors. Use judgment when reporting them.
- **Warnings do not block execution.** When ambiguous or multiple columns are detected, the script proceeds with the best available interpretation and surfaces warnings for the user to review.
- **This skill audits data quality only.** It does not classify accounts, suggest journal entries, or provide accounting or tax advice.
