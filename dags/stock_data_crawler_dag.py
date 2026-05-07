import os
import sys
import gc
import logging
import requests
import pandas as pd
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL connection string
conn_str = os.getenv('DATABASE_RENDER')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# conn_str = 'postgresql://stock_data_i36c_user:YLMLHhfjF7oIdi3SMzexVaobFuaL37Dc@dpg-csro9ppu0jms73e1epb0-a.singapore-postgres.render.com/stock_data_i36c'
engine = create_engine(conn_str)

new_column_names = [
    'trade_date', 
    'listed_shares', 
    'shares_outstanding', 
    'reference_price', 
    'ceiling_price', 
    'floor_price', 
    'total_trading_volume', 
    'total_trading_value', 
    'market_capitalization', 
    'opening_price', 
    'closing_price', 
    'highest_price', 
    'lowest_price', 
    'difference', 
    'average_price', 
    'adjusted_closing_price', 
    'price_change', 
    'price_change_percentage', 
    'average_buy_price', 
    'average_sell_price', 
    'buy_limit', 
    'sell_limit', 
    'matched_orders_volume', 
    'matched_orders_value', 
    'total_orders_placed_buy', 
    'total_orders_placed_sell', 
    'total_volume_placed_buy', 
    'total_volume_placed_sell',
    'agreements_volume',
    'agreements_value'
]

def fetch_stock_codes():
    try:
        with engine.connect() as connection:
            query = text("SELECT code FROM stock_info")
            result = connection.execute(query)
            return [row['code'] for row in result]
    except Exception as e:
        logging.error(f"Error fetching stock codes: {e}")
        return []
    
def download_data_to_dataframe(code, from_date, to_date, page_index=1, page_size=10):

    url = f"https://finance.vietstock.vn/data/ExportTradingResult?Code={code}&OrderBy=&OrderDirection=desc&PageIndex={page_index}&PageSize={page_size}&FromDate={from_date}&ToDate={to_date}&ExportType=excel&Cols=KLNY%2CKLCPDLH%2CGTC%2CT%2CS%2CTKLGD%2CTGTGD%2CVHTT%2CMC%2CTGG%2CLDM%2CDC%2CTGPTG%2CLDB%2CCN%2CBQM%2CLDMB%2CTN%2CBQB%2CKLDM%2CGYG%2CDM%2CKLDB%2CBQ%2CDB%2CKLDMB%2CGDC%2CKLGDKL%2CGTGDKL%2CKLGDTT%2CGTGDTT&ExchangeID=5"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36',
        'Referer': 'https://finance.vietstock.vn/ACV/thong-ke-giao-dich.htm',
    }

    try:

        response = requests.get(url, headers=headers)
        response.raise_for_status()  
        soup = BeautifulSoup(response.content, "html.parser")
        tables = soup.find_all("table")
        df = pd.read_html(str(tables[1]))[0] 
        return df
    
    except Exception as e:
        logging.error(f"Error downloading data for {code}: {e}")
        return None

def insert_data_to_db(df, table_name):
    try:
        with engine.connect() as connection:

            for _, row in df.iterrows():

                query = text("""
                    SELECT COUNT(*) FROM stock_data 
                    WHERE trade_date = :trade_date AND stock_code = :stock_code
                """)
                result = connection.execute(query, {'trade_date': row['trade_date'], 'stock_code': row['stock_code']})
                count = result.scalar()

                if count == 0:
                    row.to_frame().T.to_sql(table_name, con=connection, if_exists='append', index=False)
                else:
                    logging.info(f"Duplicate entry for {row['trade_date']} and {row['stock_code']}, skipping.")
    except Exception as e:
        logging.error(f"Error inserting data to {table_name}: {e}")


def process_stock_data(code, from_date, to_date):

    logging.info(f"Processing stock code {code}...")
    df = download_data_to_dataframe(code, from_date, to_date)
    
    if df is not None:
        try:
            df = df.drop(df.columns[[29, 26]], axis=1)
            df.columns = new_column_names
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%d/%m/%Y').dt.strftime('%Y-%m-%d')
            df.insert(1, 'stock_code', code)
            df.replace("-", None, inplace=True)
            insert_data_to_db(df, table_name="stock_data")
            logging.info(f"Successfully processed data for {code}.")

        except Exception as e:
            logging.error(f"Error processing data for {code}: {e}")
    else:
        logging.info(f"No data available for {code}.")


def update_database(ticker_list, from_date, to_date, max_workers=5):

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_stock_data, code, from_date, to_date) for code in ticker_list]
        for future in as_completed(futures):
            future.result()


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'stock_data_update',
    default_args=default_args,
    description='A DAG to update stock data daily',
    schedule_interval='0 0 * * *',
    start_date=datetime(2024, 10, 1, 0, 0),
    catchup=False,
) as dag:
    
    def run_update_database():

        from_date = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        to_date = datetime.today().strftime('%Y-%m-%d')
        ticker_list = fetch_stock_codes()

        if ticker_list:
            update_database(ticker_list, from_date, to_date, max_workers=10)

    update_stock_data_task = PythonOperator(
        task_id='update_stock_data',
        python_callable=run_update_database,
    )

    update_stock_data_task
