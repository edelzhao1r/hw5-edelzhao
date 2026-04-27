# hw5-edelzhao: Trial Balance Auditor

## Overview
A reusable AI skill for auditing CSV trail balances

## What this skill does

`trial-balance-auditor` is a reusable AI skill that audits a CSV trial balance file. It automatically detects debit and credit columns regardless of naming convention, computes totals, checks whether the books balance, and flags data quality issues including missing values, negative entries, and statistical outliers.

The final output is a structured JSON report that the agent interprets into a clear, human-readable audit summary.

---

## Why I chose it

Trial balance validation is a task that sounds simple but is genuinely unreliable when left to a language model alone. A model can describe what a balanced trial balance should look like, but it cannot consistently parse arbitrary column names, sum large sets of numbers without error, or apply a z-score threshold to flag outliers. These are deterministic operations — they need code.

At the same time, the *interpretation* of the results (explaining what a 7,300 discrepancy means, recommending next steps, flagging which rows deserve attention) is exactly where a language model adds value. This skill draws a clean line between what code must do and what the model should do, which is the core idea of Week 5.

The audit domain also felt personally meaningful — having worked in auditing, I know that data quality issues in a trial balance are rarely obvious at a glance. A tool like this would have been genuinely useful.

---

## How to use it

### Prerequisites

```bash
pip install pandas
```

### Folder structure

```
.agents/skills/trial-balance-auditor/
├── SKILL.md
└── scripts/
    └── audit.py
```

### Running the script directly

```bash
python3 scripts/audit.py path/to/your/trial_balance.csv
```

Adjust outlier sensitivity (default z-threshold is 3.0):

```bash
python3 scripts/audit.py path/to/your/trial_balance.csv --z-threshold 2.5
```

### Using with Claude Code

Place the skill folder under `.agents/skills/` in your project, then prompt Claude Code naturally:

```
Can you audit my trial balance? The file is at data/q3_trial_balance.csv
```

Claude Code will detect the skill from its name and description, run the script, and return a narrative audit report.

---

## What the script does

`audit.py` performs the following steps:

1. **Loads the CSV** and validates that the file exists and is readable
2. **Classifies columns** using keyword matching into debit (strong/weak) and credit (strong/weak) categories — supporting names like `Debit Amount`, `Dr.`, `Cash Debit`, `Charges`, and more
3. **Emits warnings** when column matches are ambiguous or when multiple columns of the same type are found and will be merged
4. **Coerces values to numeric**, treating unparseable entries as missing
5. **Detects missing values** across all identified debit and credit columns
6. **Computes totals** by summing across all matched columns
7. **Checks balance** using a floating-point safe comparison (`math.isclose`)
8. **Flags anomalies**: negative values (always flagged) and statistical outliers (z-score above threshold, requiring at least 4 data points)
9. **Outputs a JSON report** with an overall `PASS` or `FAIL` status

---

## What worked well

- The two-tier keyword system (strong vs. weak match) handles real-world column naming variation gracefully without requiring the user to rename their file
- Merging multiple debit/credit columns while surfacing warnings strikes a good balance between being helpful and being transparent
- Keeping the script output as structured JSON makes it easy for the model to generate a flexible narrative rather than being locked into a fixed template
- The `--z-threshold` flag gives users a simple way to tune sensitivity without touching the code

## Limitations

- Column detection is heuristic and may fail on highly unconventional naming — the script returns the full column list in the error message to help the user troubleshoot
- Outlier detection is skipped for columns with fewer than 4 numeric rows
- The skill audits data quality only — it does not suggest correcting entries, classify accounts, or provide accounting advice
- Multi-currency files are not handled; all values are treated as a single unit

---

## Walkthrough Video
