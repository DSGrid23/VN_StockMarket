import requests
import pandas as pd
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import create_engine, text
from functools import partial
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL connection string
conn_str = os.getenv('DATABASE_RENDER')

url = 'https://finance.vietstock.vn/data/KQGDThongKeGiaStockPaging'
headers = {
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Cookie': '_cc_id=ce2a8a9af12c25ef62ea562aea3dae6a; dable_uid=53044722.1710493651471; language=vi-VN; panoramaId_expiry=1731583626247; panoramaId=0598c25719d689992ff88c1edf2e16d5393841442e7aa21c6436e6cff5b2d12a; panoramaIdType=panoIndiv; Theme=Light; AnonymousNotification=; isShowLogin=true; ASP.NET_SessionId=syqi43kudrtmvg3w55pb20vu; __RequestVerificationToken=oNJsYbwv2IZJX7W5XlbKc7NysT92N8lQXuZmvBinS7PWw0kHlGvgSwo44cAzjvnnSVxErLrJKyRYgTQA_jKkd9viB6tL915Jj-jVkzdBE6I1; _gid=GA1.2.1745738540.1731569426; __gads=ID=903a4cbbe3ca3d50:T=1727447519:RT=1731569435:S=ALNI_MYFCdIm-lok4f-TW-oEcWT6TTe9LQ; __gpi=UID=00000f207bdbf994:T=1727447519:RT=1731569435:S=ALNI_MaMh_LC-Xx6e-M4IMV08vSXLimbSw; __eoi=ID=73503c8998817043:T=1727447519:RT=1731569435:S=AA-AfjaJCqHisvyIHcv8oKV2ekSp; finance_viewedstock=ACV,VCB,; vts_usr_lg=0F5988E5A9BAA11EF44F320EE70F3E59CD6D185BFA1DC04B7F778C777C3F5BD204295ABF46E750D08F1D2E70F3536BABEB1109208F94DEC757FBF07CD0E13AAD3865DD00A14F2596A7BBF389593F169B3DE9CDD85CC7F66BD068C08DE7ED795C435D62642A74EA15C9B4FFEE51D9480F8608259FFF81FC485ED52A7F5C74D407; vst_usr_lg_token=7gjga8OTokaEyfxu9LLosw==; _ga_EXMM0DKVEX=GS1.1.1731569424.14.1.1731569718.10.0.0; _ga=GA1.2.1647043453.1727447451; cto_bundle=wTMQu19rS3JUaXdNQVlKNFZnWDJrVkJlSjFEUDNucHdHMSUyRmdUM2h3MTNKYXc4ajRHNWtBRVR1U0JmOCUyRkptS3RtOGQ3cGpxc2xnVGhyaUlRaXdORGJqYTRoalVnRUhnMTVmVEJEMEJmbjVSc25BNVRUZzhQaTFac3B6Y01rU0ppNWp2dDhjRm1udHJUVk9oTElsZWExam5LWHlOdmJiN2NLcmtwaCUyQlFWUlVVVEUlMkJGVmkxcWpoMmdzUlQyNW1DWWo5WjFHUA; cto_bidid=aWT0j19wdWpMdmc3RGxmY05YSzZ0WXFnNlF4N2xmdFhwM3RERXdsakNYbkdURW9GaU5VOVhTU3VHaHF6MG1pdCUyRk8zTzZHWGg4NTlSSUxOeFhUMFFJRGNTRGwwTEpNVWl0MmJqRUpaUiUyQnl5VlBUWHdzNTFwamhmVTZvTXdpJTJGemp2VTlQZE11T3RlNEhtaWtab01nQ2ZINFpqVVElM0QlM0Q; cto_dna_bundle=V7f3pl9rS3JUaXdNQVlKNFZnWDJrVkJlSjFDTUdYTjFQdVFxUlQ0bHZpcXFVeDRteVQwWTJDaGNZZVBxWDlTZGExSWNTZmczV3dOdWJTYUh3QmZzQ2YwQXVXZyUzRCUzRA; cto_bundle=rUyApl9rS3JUaXdNQVlKNFZnWDJrVkJlSjFDQXpRaFRUZnFXdUJBNWVtY1F3RE9oNEwlMkJ4dzZzazQ2cmZQQUVSZ1hkSjgxemxzbHkyRzVGSGE5eEM3UHNMV01YdFE3T1JuMkVLT0ZIYmp3UHFLSlZxM3pZODFGeUQyWm1rYzhjaVpzdDIwcHlVJTJCY0ExUXBpMTNrTXEyYm9Wc25mZDkwU3R5MmtUOUVtZGpOVmIyaDJYNnlsdUw2QTY0YjY0dVMlMkI3Z0xaN3A',
    'Origin': 'https://finance.vietstock.vn',
    'Referer': 'https://finance.vietstock.vn/ket-qua-giao-dich',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
    'X-Requested-With': 'XMLHttpRequest',
    'sec-ch-ua': '"Chromium";v="130", "Microsoft Edge";v="130", "Not?A_Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"'
}
base_data = {
    'page': '1',
    'pageSize': '20',
    'fromDate': '2022-10-14',
    'toDate': '2024-11-14',
    '__RequestVerificationToken': 'rVyx37ITw6hQwfsQvpO4hXz3meH5pFr8LTLDPh8tRhLCYYooaEH5u5KkgyaCFzImSZJY7xOQ-bhoCOgqyzXJQzQGORZhqqdEp8NRZsNXDPICO2hXg9ekQLIksNqChCnT0'
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

# conn_str = 'postgresql://stock_data_i36c_user:YLMLHhfjF7oIdi3SMzexVaobFuaL37Dc@dpg-csro9ppu0jms73e1epb0-a.singapore-postgres.render.com/stock_data_i36c'
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

    # Insert data into database
    try:
        with engine.connect() as conn:
            all_data.to_sql('stock_index', con=conn, if_exists='append', index=False, method='multi')
        logging.info(f"Data for {index_name} inserted successfully.")
    except Exception as e:
        logging.error(f"Failed to insert data for {index_name}: {e}")

def fetch_process_insert_data():
    # Call the existing code logic here
    try:
        # The entire logic for stock data extraction, processing, and insertion
        logging.info("Starting the extraction process.")
        
        # Assuming `fetch_and_insert_data` is a function you've defined
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Create a partial function for passing arguments
            futures = [executor.submit(fetch_and_insert_data, index_name, catID, stockID)
                    for index_name, (catID, stockID) in indices.items()]
            for future in futures:
                future.result()  # Wait for all tasks to complete
                
        logging.info("Data extraction and insertion completed successfully.")
    except Exception as e:
        logging.error(f"An error occurred during data processing: {e}")
        raise  # Raise the exception to mark the task as failed in Airflow

logging.info("Data extraction and insertion completed!")

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'catchup': False,
}

dag = DAG(
    'stock_index_data_crawler',
    default_args=default_args,
    description='Fetch, process, and insert stock data',
    schedule_interval='0 0 * * *',
    start_date=datetime(2024, 10, 1, 0, 0),
)

crawl_task = PythonOperator(
    task_id='fetch_process_insert_stock_data',
    python_callable=fetch_process_insert_data,
    dag=dag,
    retries=1,  
    retry_delay=timedelta(minutes=5),  # Retry delay
)

crawl_task