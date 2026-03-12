import os
import gspread
import yfinance as yf
from datetime import datetime, timedelta
import time
import argparse
from tqdm import tqdm

# --- 1. Argument Parser ---
parser = argparse.ArgumentParser(description="Fetch option prices from Google Sheets.")
parser.add_argument('--output', choices=['csv', 'table'], default='table', help="Output format")
parser.add_argument('--columns', default="Ticker,Type,Qty,Value", help="Columns to display")
parser.add_argument('--no-header', action='store_true', help="Do not print column names/headers")
parser.add_argument('--file', default=None, help="Optional file path to write the output to")

default_creds = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json")
parser.add_argument('--creds', default=default_creds, help="Path to Google JSON credentials")

args = parser.parse_args()
selected_cols = [c.strip() for c in args.columns.split(',')]

# --- 2. Helpers ---
def safe_float(value):
    clean_val = str(value).strip().replace(',', '')
    if not clean_val or clean_val == '-': return 0.0
    return float(clean_val)

def convert_date(serial_date):
    if not serial_date: return None
    dt = datetime(1899, 12, 30) + timedelta(days=float(serial_date))
    return dt.strftime('%Y-%m-%d')

def get_option_mid_price(ticker_obj, expiry, strike, option_type):
    chain = ticker_obj.option_chain(expiry)
    data = chain.puts if option_type == 'P' else chain.calls
    row = data[data['strike'] == float(strike)]
    if row.empty:
        # FIXME
        #raise ValueError("Failed to get option mid price: %s" % ticker_obj)
        return 0.0

    bid, ask = row.iloc[0]['bid'], row.iloc[0]['ask']
    return (bid + ask) / 2 if (bid or ask) else row.iloc[0]['lastPrice']

# --- 3. Setup ---
gc = gspread.service_account(filename=args.creds)
sh = gc.open("Money")
worksheet = sh.worksheet("Trades")

all_rows = worksheet.get_all_values(value_render_option='UNFORMATTED_VALUE')
active_trades = [row for row in all_rows[1:] if len(row) >= 17 and str(row[1]).strip() == '*']

results = []

# --- 4. Main Loop ---
pbar = tqdm(active_trades, desc="Initializing", unit="trade", leave=False)
for row in pbar:
    contracts   = int(safe_float(row[8]))
    expiry      = convert_date(row[4])
    ticker_sym  = str(row[9]).strip()
    trade_type  = str(row[13]).strip()
    put_strike  = safe_float(row[14])
    call_strike = safe_float(row[15])
    spread      = safe_float(row[16])

    pbar.set_description(f"Processing {ticker_sym}")

    tk = yf.Ticker(ticker_sym)
    price_per_share = 0.0

    if not expiry: raise ValueError("Invalid Expiry")

    if trade_type == "LEAPS":
        price_per_share = get_option_mid_price(tk, expiry, call_strike, 'C')
    elif trade_type in ["CC", "S CALL"]:
        price_per_share = -get_option_mid_price(tk, expiry, call_strike, 'C')
    elif trade_type == "CSP":
        price_per_share = -get_option_mid_price(tk, expiry, put_strike, 'P')
    elif trade_type == "S STRG":
        p = get_option_mid_price(tk, expiry, put_strike, 'P')
        c = get_option_mid_price(tk, expiry, call_strike, 'C')
        price_per_share = -(p + c)
    elif trade_type == "PCS":
        mid = get_option_mid_price(tk, expiry, put_strike, 'P') - \
              get_option_mid_price(tk, expiry, put_strike - spread, 'P')
        price_per_share = -mid
    elif trade_type == "CCS":
        mid = get_option_mid_price(tk, expiry, call_strike, 'C') - \
              get_option_mid_price(tk, expiry, call_strike + spread, 'C')
        price_per_share = -mid
    elif trade_type == "CDS":
        mid = get_option_mid_price(tk, expiry, call_strike, 'C') - \
              get_option_mid_price(tk, expiry, call_strike + spread, 'C')
        price_per_share = mid
    elif trade_type == "IC":
        p_spread = get_option_mid_price(tk, expiry, put_strike, 'P') - \
                   get_option_mid_price(tk, expiry, put_strike - spread, 'P')
        c_spread = get_option_mid_price(tk, expiry, call_strike, 'C') - \
                   get_option_mid_price(tk, expiry, call_strike + spread, 'C')
        price_per_share = -(p_spread + c_spread)
    else:
        raise ValueError("Unknown trade type: %s" % trade_type)

    total_value = price_per_share * 100 * contracts

    row_dict = {
        "Ticker": ticker_sym,
        "Type": trade_type,
        "Qty": contracts,
        "Value": f"{total_value:.2f}"
    }

    results.append([str(row_dict.get(col, "N/A")) for col in selected_cols])
    time.sleep(0.5)

# --- 5. Output Construction ---
output_lines = []

if args.output == 'csv':
    if not args.no_header:
        output_lines.append(",".join(selected_cols))
    for r in results:
        output_lines.append(",".join(r))
else:
    widths = [max(len(col), 10) for col in selected_cols]
    if not args.no_header:
        header = " | ".join([f"{col:<{widths[i]}}" for i, col in enumerate(selected_cols)])
        output_lines.append(header)
        output_lines.append("-" * len(header))
    for r in results:
        output_lines.append(" | ".join([f"{val:<{widths[i]}}" for i, val in enumerate(r)]))

# --- 6. Final Output ---
final_content = "\n".join(output_lines)

if args.file:
    with open(args.file, 'w') as f:
        f.write(final_content)
    print(f"\nOutput successfully written to {args.file}")
else:
    print("\n" + final_content)
