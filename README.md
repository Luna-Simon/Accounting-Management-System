# Accounting Management System

A desktop double-entry bookkeeping application built with **Python** and **Tkinter**, featuring Excel import/export, a Chart of Accounts, journal entries, trial balance, and local SQLite storage.

## Features

- **Double-entry bookkeeping** — journals, adjustments, and auto-balanced entries
- **Chart of Accounts** — add, edit, and manage account codes/names/types
- **Business Transactions & Adjustments tabs** — enter journal entries manually
- **Trial Balance** — view debit/credit totals per account
- **Excel Import** — import Chart of Accounts, transactions, adjustments, and General Ledger (T-account) worksheets from `.xlsx`/`.xls`
- **Excel/CSV Export** — export the current tab to CSV; export import templates to Excel
- **Local SQLite database** — data stored in `accounting.db` (ignored by git)
- **Dark mode UI** with themed Tkinter widgets
- **Keyboard shortcuts** — `Ctrl+I` import, `Ctrl+E` export, `Ctrl+Q` quit, `Ctrl+Tab` navigate

## Project Structure

```
accounting_system/
├── main.py            # Application entry point and main window (tkinter)
├── accounting.py      # Core accounting logic (trial balance, worksheet, income statement)
├── store.py           # Data layer: SQLite storage, Excel import/export (Book class)
├── logic.py           # Shared helpers: cleaning, scaling, journal balancing
├── money.py           # Money parsing and formatting (cents-based Decimal math)
├── accounting.db      # Local SQLite database (created at runtime, gitignored)
├── test_import.xlsx   # Sample Excel import file
├── README.md          # This file
├── .gitignore         # Git ignore rules
└── ui/                # Tkinter UI modules
    ├── __init__.py
    ├── theme.py       # Dark theme colors and widget options
    ├── widgets.py     # Reusable UI widgets
    ├── dashboard_tab.py
    ├── trial_tab.py
    ├── chart_tab.py
    └── journal_tab.py
```

## Requirements

- Python 3.8+
- `pandas`
- `openpyxl` (for Excel `.xlsx` support)

Install dependencies:

```bash
pip install pandas openpyxl
```

## Running the Application

```bash
python main.py
```

The app opens with a `1300x800` window containing these tabs:

| Tab | Purpose |
|-----|---------|
| Dashboard | Overview of the books |
| Trial Balance | Debit/credit summary per account |
| Chart of Accounts | Manage account codes, names, types |
| Business Transactions | Enter regular journal entries |
| Adjustments | Enter adjusting journal entries |

## Excel Import Guide

Supported import formats (auto-detected by sheet name/columns):

1. **Simple format** — columns: `Date, Description, Account, Debit, Credit`
2. **Chart of Accounts** — columns: `Code, Name, Type, Normal`
   - Types: `Asset, Liability, Equity, Revenue, Cost of Sales, Expense`
   - Normal: `Debit` or `Credit`
3. **General Ledger (T-account)** — sheet named `General Ledger` or `Ledger`
4. **Adjustments** — sheet named `Adjustments` with lines like `(a) Laundry Supplies used, 27,000`

Use **File → Import Chart of Accounts** for COA, or open the **Business Transactions** / **Adjustments** tab and import from Excel there.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+I` | Import Chart of Accounts |
| `Ctrl+E` | Export current tab to CSV |
| `Ctrl+Q` | Quit |
| `Ctrl+Tab` | Next tab |
| `Ctrl+Shift+Tab` | Previous tab |
| `Ctrl+A` | Select all rows (in table) |
| `Ctrl+C` | Copy selected rows |
| `Double-click` | Edit an entry |
| `Tab` / `Enter` | Next field in entry form |
| `Escape` | Clear form |

## License

This project is provided as-is for educational and personal use.
