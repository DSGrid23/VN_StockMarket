import os
import requests
import pandas as pd
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import create_engine, text
from functools import partial

# API and database configuration
url = 'https://finance.vietstock.vn/data/KQGDThongKeGiaStockPaging'
headers = {
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',

    'Cookie': 'language=vi-VN; ASP.NET_SessionId=3xjdn5fskb5jz53z05gftraa; __RequestVerificationToken=CrZSjaTyuqPZcTbS0qcNTEXG8UPEjCrfdt1FWgoOFKQ3kccgKKQKeNblwHj-CaNCH8Ksw6Eb8mtnABeXORn0XmTDOXz8xAQ8GzxybiKln_41',

    'Origin': 'https://finance.vietstock.vn',
    'Referer': 'https://finance.vietstock.vn/ket-qua-giao-dich?exchange=4',

    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',

    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0',

    'X-Requested-With': 'XMLHttpRequest',

    'sec-ch-ua': '"Chromium";v="148", "Microsoft Edge";v="148", "Not/A)Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"'
}
base_data = {
    'page': '1',
    'pageSize': '20',
    'fromDate': '2025-05-13',
    'toDate': '2026-05-13',
    '__RequestVerificationToken': 'OyNxxKxMsRE18zJCAvxSxEJt6dYp8LxuO1aUi8cGGwC0ajLmotNjnOGjITKFKkWzJuZ9ze_EYjTW3TPGkEiHU-FehaCAeV4x3FcjqiUxA781'
}

indices = {
    "VNIndex": (1, -19),
    "HNXIndex": (2, -18),
    "VN30Index": (4, -16),
    "HNX30Index": (5, -15),
    "UPCoMIndex": (3, -17)
}

field_names = {
    'TradingDate': 'trading_date',
    'StockCode': 'stock_code',
    'BasicPrice': 'reference_price',
    'OpenPrice': 'opening_price',
    'ClosePrice': 'closing_price',
    'HighestPrice': 'highest_price',
    'LowestPrice': 'lowest_price',
    'AvrPrice': 'average_price',
    'Change': 'price_change',
    'PerChange': 'price_change_percentage',
    'M_TotalVol': 'matched_orders_volume',
    'M_TotalVal': 'matched_orders_value',
    'TotalVol': 'total_trading_volume',
    'TotalVal': 'total_trading_value',
    'MarketCap': 'market_capitalization',
}

conn_str = os.getenv('DATABASE_RENDER')
engine = create_engine(conn_str)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def create_stock_index_table(engine):
    create_table_query = """
    CREATE TABLE IF NOT EXISTS stock_index (
        trading_date DATE,
        stock_code VARCHAR(20),
        reference_price NUMERIC,
        opening_price NUMERIC,
        closing_price NUMERIC,
        highest_price NUMERIC,
        lowest_price NUMERIC,
        average_price NUMERIC,
        price_change NUMERIC,
        price_change_percentage NUMERIC,
        matched_orders_volume BIGINT,
        matched_orders_value BIGINT,
        total_trading_volume BIGINT,
        total_trading_value BIGINT,
        market_capitalization DECIMAL(20, 2),
        PRIMARY KEY (trading_date, stock_code)
    );
    """
    with engine.connect() as connection:
        connection.execute(text(create_table_query))

# Call the function to create the table
create_stock_index_table(engine)

# Helper function to convert date format
def convert_date(date_str):
    timestamp = int(date_str.strip('/Date()')) / 1000
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')

def process_index(index_name, catID, stockID, page, all_data):
    try:
        data = base_data.copy()
        data.update({
            'catID': str(catID),
            'stockID': str(stockID),
            'page': str(page)
        })

        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            try:
                response_data = response.json()

                trading_data = response_data[1]

                if not trading_data:
                    return all_data

                df = pd.DataFrame(trading_data)

                df['TradingDate'] = df['TradingDate'].apply(convert_date)

                all_data = pd.concat([all_data, df], ignore_index=True)
                return all_data
            except ValueError:
                logging.error(f"Error processing JSON on page {page} for {index_name}.")
                return all_data
        else:
            logging.warning(f"Failed to fetch page {page} for {index_name}.")
            return all_data
    except Exception as e:
        logging.error(f"Error processing {index_name} on page {page}: {e}")
        return all_data

def fetch_and_insert_data(index_name, catID, stockID):
    page = 1
    all_data = pd.DataFrame()
    logging.info(f"Processing {index_name}...")

    while True:
        new_data = process_index(index_name, catID, stockID, page, all_data)

        if len(new_data) == len(all_data):  # No new data, break loop
            break

        all_data = new_data
        page += 1

    # Rename columns based on field names
    all_data = all_data[field_names.keys()]
    all_data = all_data.rename(columns=field_names)
    print(all_data.head())

    # Insert data into database
    try:
        with engine.connect() as conn:
            all_data.to_sql('stock_index', con=conn, if_exists='append', index=False, method='multi')
        logging.info(f"Data for {index_name} inserted successfully.")
    except Exception as e:
        logging.error(f"Failed to insert data for {index_name}: {e}")

# Parallel processing using ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=5) as executor:
    # Create a partial function for passing arguments
    futures = [executor.submit(fetch_and_insert_data, index_name, catID, stockID)
               for index_name, (catID, stockID) in indices.items()]

    for future in futures:
        future.result()  # Wait for all tasks to complete

logging.info("Data extraction and insertion completed!")

