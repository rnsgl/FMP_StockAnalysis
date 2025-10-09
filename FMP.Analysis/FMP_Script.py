import requests
import pandas as pd
import mysql.connector
import yfinance as yf
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os

import time

# Configuration


PERIOD = "FY"
LIMIT = 5
EVENT_WINDOW = 3

# Just 5 major companies
COMPANIES = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']



def config_from_env():
    load_dotenv()


def fetch_growth_metrics(symbol, period, limit=LIMIT):
    url = f"https://financialmodelingprep.com/stable/income-statement-growth?symbol={symbol}&period={period}&limit={limit}&apikey={os.getenv('API_KEY')}"
    resp = requests.get(url)
    if resp.status_code != 200:
        return pd.DataFrame()
    try:
        data = resp.json()
    except:
        return pd.DataFrame()
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    wanted_cols = ["symbol", "date", "fiscalYear", "period",
                   "growthRevenue", "growthGrossProfit", "growthOperatingIncome",
                   "growthNetIncome", "growthEPS", "growthEPSDiluted"]
    existing_cols = [c for c in wanted_cols if c in df.columns]
    return df[existing_cols]

def fetch_stock_prices(symbol):
    
    url = f"https://financialmodelingprep.com/stable/historical-price-eod/light?symbol={symbol}&apikey={os.getenv('API_KEY')}"
    resp = requests.get(url)
    if resp.status_code != 200:
        return pd.DataFrame()
    try:
        data = resp.json()
    except:
        return pd.DataFrame()
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)

    if "close" in df.columns:
        df = df.rename(columns={"close": "price"})
    df = df[["symbol", "date", "price", "volume"]].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df

def fetch_earnings_dates(symbol, n=4):
    """
    Retrieve the company's past `n` earnings release dates using yfinance.
    Returns a DataFrame with columns: symbol, date (datetime.date)
    """
    t = yf.Ticker(symbol)
    try:
        ed = t.get_earnings_dates()
    except Exception:
        return pd.DataFrame()
    if ed is None or ed.empty:
        return pd.DataFrame()

   
    if isinstance(ed.index, pd.DatetimeIndex):
        dates = pd.to_datetime(ed.index).date
    else:
        
        if 'Earnings Date' in ed.columns:
            dates = pd.to_datetime(ed['Earnings Date']).dt.date
        elif 'startdatetime' in ed.columns:
            dates = pd.to_datetime(ed['startdatetime']).dt.date
        else:
           
            try:
                dates = pd.to_datetime(ed.iloc[:, 0]).dt.date
            except Exception:
                return pd.DataFrame()

    df = pd.DataFrame({"symbol": symbol, "date": dates})
   
    today = datetime.now(timezone.utc).date()
    df = df[df["date"] <= today]
    df = df.sort_values("date", ascending=False).drop_duplicates(subset=["date"])
    return df.head(n)

def create_symbols_table(conn):
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS stock_symbols (
        symbol VARCHAR(10) PRIMARY KEY,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    cur.close()

def upsert_stock_prices(conn, df):
    if df.empty:
        return
    cur = conn.cursor()
    for _, row in df.iterrows():
        cur.execute("""
        INSERT INTO stock_prices (symbol, date, price, volume)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE price=VALUES(price), volume=VALUES(volume)
        """, (row["symbol"], row["date"], float(row["price"]), int(row["volume"] if not pd.isna(row["volume"]) else 0)))
    conn.commit()
    cur.close()

def insert_growth(conn, df):
    if df.empty:
        return
    cur = conn.cursor()
    cols = df.columns.tolist()
    placeholders = ", ".join(["%s"] * len(cols))
    col_names = ", ".join(cols)
    for _, row in df.iterrows():
        values = [None if pd.isna(x) else x for x in row[cols].tolist()]
        cur.execute(f"INSERT INTO income_growth ({col_names}) VALUES ({placeholders})", tuple(values))
    conn.commit()
    cur.close()

def insert_earnings(conn, df):
    if df.empty:
        return
    cur = conn.cursor()
    for _, row in df.iterrows():
        cur.execute("""
        INSERT IGNORE INTO earnings_reports (symbol, earnings_date) VALUES (%s, %s)
        """, (row["symbol"], row["date"]))
    conn.commit()
    cur.close()

def compute_and_insert_reactions(conn, symbol, earnings_dates, prices_df):
    if earnings_dates.empty:
        return
    prices_df = prices_df.sort_values("date")
    
    def get_price_on_or_before(target_date):
        subs = prices_df[prices_df["date"] <= target_date]
        if subs.empty:
            return None
        return float(subs.iloc[-1]["price"])
    cur = conn.cursor()
    for _, er in earnings_dates.iterrows():
        ed = er["date"]
        start = ed - timedelta(days=EVENT_WINDOW)
        end = ed + timedelta(days=EVENT_WINDOW)
        price_before = get_price_on_or_before(start)
        price_after = get_price_on_or_before(end)
        if price_before is None or price_after is None:
            continue
        pct_change = ((price_after - price_before) / price_before) * 100 if price_before != 0 else None
        cur.execute("""
        INSERT INTO event_reactions (symbol, earnings_date, window_start, window_end, price_before, price_after, pct_change)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (symbol, ed, start, end, price_before, price_after, pct_change))
    conn.commit()
    cur.close()

def run_etl():
    conn = None
    try:
        conn = mysql.connector.connect(**os.getenv('MYSQL_CONFIG'))
        create_symbols_table(conn)
        
        all_growth = []
        all_prices = []
        
        for idx, sym in enumerate(COMPANIES, 1):
            try:
                print(f"[{idx}/{len(COMPANIES)}] Processing {sym}...")
                
                growth_df = fetch_growth_metrics(sym, PERIOD, LIMIT)
                if not growth_df.empty:
                    insert_growth(conn, growth_df)
                    all_growth.append(growth_df)

                prices_df = fetch_stock_prices(sym)
                if not prices_df.empty:
                    upsert_stock_prices(conn, prices_df)
                    all_prices.append(prices_df)
                else:
                    print(f"No price data for {sym}")
                    continue

                earnings_df = fetch_earnings_dates(sym, n=8)
                if not earnings_df.empty:
                    insert_earnings(conn, earnings_df)
                    compute_and_insert_reactions(conn, sym, earnings_df, prices_df)

                time.sleep(0.25)  #
                
            except Exception as e:
                print(f"Error processing {sym}: {e}")
                time.sleep(0.5)
                continue

        return (pd.concat(all_growth) if all_growth else pd.DataFrame(),
                pd.concat(all_prices) if all_prices else pd.DataFrame())
                
    except Exception as e:
        print(f"Fatal error: {e}")
        return pd.DataFrame(), pd.DataFrame()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    growth_df, prices_df = run_etl()
    print("ETL concluído.")
  




