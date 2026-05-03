# --- Core Libraries ---
import numpy as np
import pandas as pd
# import statsmodels.api as sm
import matplotlib.pyplot as plt
import seaborn as sns
import requests
import time
 
# --- Database & System Libraries ---
import os
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta
 
# --- Import Custom DB Connector ---
from common.database.MQSDBConnector import MQSDBConnector
 
# --- Configuration ---
pd.set_option('display.max_columns', None)
pd.set_option('display.float_format', lambda x: '%.4f' % x)
sns.set_theme(style="whitegrid")
 
# Configure logging for better debugging and tracing
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
 
# Load environment variables
load_dotenv()
 
 
def _get_market_data(tickers_list: list, lookback_days: int, api_key: str) -> pd.DataFrame:
    """
    Fetches daily (end-of-day) historical data from the FMP API.
    
    This version loops by year to try and bypass API limits.
    WARNING: This will likely NOT work if the API key plan itself
             restricts historical data access to only 1 year.
    
    :param tickers_list: List of stock symbols
    :param lookback_days: How many days of data to fetch
    :param api_key: The FMP API key
    :return: Pandas DataFrame of historical records
    """
    
    # --- 1. Prepare Parameters ---
    if not tickers_list:
        logging.warning("No tickers provided. Returning empty DataFrame.")
        return pd.DataFrame()
        
    tickers_str = ",".join(tickers_list)
    
    # Calculate start and end years for the loop
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    
    start_year = start_date.year
    end_year = end_date.year  # This will be the current year
 
    all_dfs = []  # List to hold DataFrame for each year
    
    logging.info(f"Starting yearly data fetch from {start_year} to {end_year} for {tickers_str}...")
 
    # --- 2. Loop Through Each Year ---
    for year in range(start_year, end_year + 1):
        
        # Define the date range for this specific year
        from_date_loop = f"{year}-01-01"
        to_date_loop = f"{year}-12-31"
        
        # Override 'to_date' if we are in the current year
        if year == end_year:
            to_date_loop = end_date.date().isoformat()
 
        logging.info(f"--- Fetching data for year: {year} ---")
 
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{tickers_str}"
        params = {"from": from_date_loop, "to": to_date_loop, "apikey": api_key}
 
        # --- Make API Request (per year) ---
        try:
            response = requests.get(url, params=params)
            response.raise_for_status() 
            data = response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed for {year}: {e}")
            continue  # Skip to next year
 
        # --- Parse FMP Response (for this year) ---
        historical_data = []
        if isinstance(data, dict) and 'historical' in data:
            logging.info(f"Processing single ticker response for {year}")
            for record in data['historical']:
                record['symbol'] = tickers_str
                historical_data.append(record)
                
        elif isinstance(data, dict) and 'historicalStockList' in data:
            logging.info(f"Processing multi-ticker response for {year}")
            for stock in data['historicalStockList']:
                t_symbol = stock['symbol']
                for record in stock['historical']:
                    record['symbol'] = t_symbol
                    historical_data.append(record)
        else:
            logging.warning(f"No valid data found for {year}.")
            
        if historical_data:
            logging.info(f"Successfully parsed {len(historical_data)} data points for {year}.")
            all_dfs.append(pd.DataFrame(historical_data))
        else:
            logging.warning(f"No data returned from API for {year}.")
            
        # **CRUCIAL**: Wait for a moment to avoid API rate limits
        # (e.g., 0.5 - 1 second between calls)
        time.sleep(0.5) 
 
    # --- 3. Combine All DataFrames ---
    if not all_dfs:
        logging.warning("No data fetched for any year. Returning empty DataFrame.")
        return pd.DataFrame()
        
    df = pd.concat(all_dfs)
 
    # --- 4. Convert to DataFrame and Clean (Run once on the final DF) ---
    df.rename(columns={
        'date': 'timestamp',
        'close': 'close_price',
        'open': 'open_price',
        'high': 'high_price',
        'low': 'low_price',
        'symbol': 'ticker'
    }, inplace=True)
 
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    num_cols = [
        'open_price', 'high_price', 'low_price', 'close_price', 'adjClose',
        'volume', 'unadjustedVolume', 'change', 'changePercent', 'vwap'
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
 
    df.dropna(subset=['timestamp', 'ticker', 'close_price'], inplace=True)
    df.sort_values(['timestamp', 'ticker'], inplace=True)
    
    # --- Add Volume Trend Feature ---
    logging.info("Calculating volume trend features...")
    grouped = df.groupby('ticker')
    
    # Calculate volume moving averages
    df['volume_ma_20'] = grouped['volume'].transform(lambda x: x.rolling(20).mean())
    df['volume_ma_50'] = grouped['volume'].transform(lambda x: x.rolling(50).mean())
    
    # Calculate volume trend (short-term vs long-term)
    df['volume_trend_20d'] = (df['volume_ma_20'] - df['volume_ma_50']) / df['volume_ma_50']
    
    # Calculate volume ratio (current vs 20-day average)
    df['volume_ratio_20d'] = df['volume'] / df['volume_ma_20']
    
    logging.info(f"Successfully processed {len(df)} TOTAL data points from all years.")
    return df
 
 
def main():
    """
    Main function to execute data fetching when run as a script.
    """
    # --- Load API Key ---
    fmp_api_key = os.getenv("FMP_API_KEY")
 
    if not fmp_api_key:
        logging.error("FMP_API_KEY not found in environment variables...")
        return None
 
    # --- Execute Data Fetching ---
    tickers = ['AAPL', 'MSFT', 'GOOG'] 
    model_lookback_days = 365 * 10  # ~10 years
 
    all_data = _get_market_data(tickers, model_lookback_days, fmp_api_key)
    
    if not all_data.empty:
        print(f"Loaded {len(all_data)} rows of end-of-day data.")
        print("\nData head:")
        print(all_data.head())
        print("\nData tail:")
        print(all_data.tail())
        
        # Show volume trend summary
        print("\n" + "="*60)
        print("VOLUME TREND SUMMARY (Recent Data):")
        print("="*60)
        for ticker in tickers:
            ticker_data = all_data[all_data['ticker'] == ticker].tail(1)
            if not ticker_data.empty and pd.notna(ticker_data['volume_trend_20d'].iloc[0]):
                trend = ticker_data['volume_trend_20d'].iloc[0] * 100
                ratio = ticker_data['volume_ratio_20d'].iloc[0]
                print(f"\n{ticker}:")
                print(f"  Volume Trend (20d vs 50d): {trend:+.1f}%")
                print(f"  Current vs 20d Avg: {ratio:.2f}x")
                
                if trend > 10:
                    print(f"  → Growing interest (volume increasing)")
                elif trend < -10:
                    print(f"  → Declining interest (volume decreasing)")
                else:
                    print(f"  → Stable volume")
    else:
        print("No data fetched.")
    
    return all_data
 
 
if __name__ == "__main__":
    print("Libraries imported and MQSDBConnector ready.")
    all_data = main()