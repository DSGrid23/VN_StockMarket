import logging
import cloudscraper
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from concurrent.futures import ThreadPoolExecutor, as_completed

import os
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL connection string
conn_str = os.getenv('DATABASE_RENDER')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# conn_str = 'postgresql://stock_data_i36c_user:YLMLHhfjF7oIdi3SMzexVaobFuaL37Dc@dpg-csro9ppu0jms73e1epb0-a.singapore-postgres.render.com/stock_data_i36c'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
}

# Define translation dictionary
FIELD_TRANSLATION = {
    'NN mua': 'foreign_buy',
    '% NN sở hữu': 'percent_foreign_ownership',
    'Cổ tức TM': 'cash_dividend',
    'T/S cổ tức': 'dividend_yield',
    'Beta': 'beta',
    'EPS': 'eps',
    'P/E': 'pe',
    'F P/E': 'forward_pe',
    'BVPS': 'bvps',
    'P/B': 'pb'
}

def convert_date_format(date_str):
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None  # Return None if the date is invalid
    

def fetch_stock_data(stock_code, url):

    scraper = cloudscraper.create_scraper()
    logging.info(f"Fetching data for stock code: {stock_code}")
    
    response = scraper.get(url, headers=HEADERS)

    if response.status_code != 200:
        logging.error(f"Failed to fetch data for {stock_code}. Status code: {response.status_code}")
        return None
    
    soup = BeautifulSoup(response.text, "html.parser")
    date_tag = soup.find('div', id='tradedate')
    date = date_tag.text.split()[0] if date_tag else "Unknown"


    table = soup.find('div', class_="row stock-price-info")


    data_dict = {}
    
    for div_class in ['col-xs-12 col-sm-5 col-md-4 col-c bg-50', 'col-xs-12 col-sm-4 col-md-4 col-c-last']:
        table_div = table.find('div', class_=div_class) if table else None
        if table_div:
            fields = table_div.find_all('p', class_='p8')

            for field in fields:
                field_name = field.contents[0].strip() if field.contents else None
                value_tag = field.find('b', class_='pull-right')
                value = value_tag.text.strip().replace(',', '') if value_tag and value_tag.text.strip() != '-' else None

                if field_name and value:
                    data_dict[FIELD_TRANSLATION.get(field_name, field_name)] = value
    
    data_dict = {
        'foreign_buy': data_dict.get('foreign_buy', '0'),
        'percent_foreign_ownership': data_dict.get('percent_foreign_ownership', '0'),
        'cash_dividend': data_dict.get('cash_dividend', '0'),
        'dividend_yield': data_dict.get('dividend_yield', '0'),
        'beta': data_dict.get('beta', '0'),
        'eps': data_dict.get('eps', '0'),
        'pe': data_dict.get('pe', '0'),
        'forward_pe': data_dict.get('forward_pe', '0'),
        'bvps': data_dict.get('bvps', '0'),
        'pb': data_dict.get('pb', '0')
    }
    logging.info(f"Data fetched for {stock_code}: {data_dict}")
    return {
        'stock_code': stock_code,
        'date': convert_date_format(date),
        **data_dict
    }

def insert_data_to_db(data, engine):
    if not data:
        return
    
    with engine.connect() as connection:
        insert_query = text("""
            INSERT INTO financial_metrics (stock_code, date, foreign_buy, percent_foreign_ownership, cash_dividend, dividend_yield, beta, eps, pe, forward_pe, bvps, pb)
            VALUES (:stock_code, :date, :foreign_buy, :percent_foreign_ownership, :cash_dividend, :dividend_yield, :beta, :eps, :pe, :forward_pe, :bvps, :pb)
            ON CONFLICT (stock_code, date) DO NOTHING;
        """)
        connection.execute(insert_query, data)
        logging.info(f"Data inserted for stock code: {data['stock_code']}")


def fetch_and_insert_stock_data():

    scraper = cloudscraper.create_scraper()
    engine = create_engine(conn_str)


    with engine.connect() as connection:
        query = text("SELECT code, url FROM stock_info")
        stock_list = connection.execute(query)
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_stock_data, row['code'], row['url']): row['code'] for row in stock_list}
            for future in as_completed(futures):
                stock_code = futures[future]
                try:
                    data = future.result()
                    insert_data_to_db(data, engine)
                except Exception as e:
                    logging.error(f"Error processing stock code {stock_code}: {e}")

        
    
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


with DAG(
    'finanical_metrics_crawler',
    default_args=default_args,
    description='Crawls stock data and inserts into database',
    schedule_interval='0 0 * * *',
    start_date=datetime(2024, 10, 1, 0, 0),
    catchup=False,
) as dag:
    
    crawl_and_store_data = PythonOperator(
        task_id='fetch_and_insert_stock_data',
        python_callable=fetch_and_insert_stock_data
    )

    crawl_and_store_data
