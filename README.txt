============================================================
PORTFOLIO SUMMARY TOOL
============================================================

A Python-based utility that retrieves options positions from
a Google Sheet and calculates their current market value
(Mid Price) using Yahoo Finance data.

--- USAGE ---

Run the script from the command line:
   python portfolio-summary.py [OPTIONS]

Options:
  --output [table|csv]    Choose output format (Default: table)
  --columns "Col1,Col2"   Comma-separated list of columns to show
                          Available: Ticker, Type, Qty, Value
  --no-header             Suppress column names and dividers
  --creds                 The path to the Google service account
                          credentials file (Default: credentials.json)

Examples:
  # View total value only
  python portfolio-summary.py --columns="Value" --no-header

  # Export all data to a CSV file
  python portfolio-summary.py --output=csv > summary.csv

--- CREDENTIALS ---

The script looks for 'credentials.json' in its own directory by default.

To use a custom path:

  python portfolio-summary.py --creds="C:\custom\path\key.json"

--- WINDOWS SHORTCUT ---

To print a summary in a Windows terminal, use a shortcut as follows:

  C:\Windows\System32\cmd.exe /k python "C:\<path-to-script>\portfolio-summary.py" --columns="Value" --no-header

--- TRADE TYPES SUPPORTED ---

- LEAPS / CDS: Long positions (Positive Value)
- CC / S CALL: Short Call (Negative Value)
- CSP: Cash Secured Put (Negative Value)
- S STRG: Short Strangle (Negative Value)
- PCS / CCS / IC: Credit Spreads (Negative Value)

============================================================
