import pandas as pd
from sqlalchemy import create_engine, text
import logging
import os
from dotenv import load_dotenv
load_dotenv()

# PostgreSQL connection string
conn_str = os.getenv('DATABASE_RENDER')
engine = create_engine(conn_str)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

df = pd.read_csv('corporate_data.csv')
df_filtered = df[['CatID', 'Exchange', 'IndustryName', 'Code', 'Name', 'URL']]
df_filtered.rename(columns={
                            'CatID': 'cat_id',
                            'Exchange': 'exchange',
                            'IndustryName': 'industry_name',
                            'Code': 'code',
                            'Name': 'name',
                            'URL' : 'url'
                            }, inplace=True)

create_table_query = """
CREATE TABLE IF NOT EXISTS stock_info (
    cat_id INTEGER,
    exchange VARCHAR(50),
    industry_name VARCHAR(200),
    code VARCHAR(50) PRIMARY KEY,
    name VARCHAR(200),
    url VARCHAR(200)
);
"""

with engine.connect() as connection:
    connection.execute(create_table_query)
logging.info("Table `stock_info` ensured to exist.")


existing_codes_query = "SELECT code FROM stock_info"

with engine.connect() as connection:
    existing_codes = set(pd.read_sql(existing_codes_query, connection)['code'])
logging.info(f"Fetched {len(existing_codes)} existing codes from the database.")

new_rows = df_filtered[~df_filtered['code'].isin(existing_codes)]
logging.info(f"Identified {len(new_rows)} new rows to insert.")

if not new_rows.empty:
    with engine.connect() as connection:
        insert_query = """
        INSERT INTO stock_info (cat_id, exchange, industry_name, code, name, url)
        VALUES (:cat_id, :exchange, :industry_name, :code, :name, :url)
        ON CONFLICT (code) DO NOTHING
        """
        try:
            connection.execute(
                text(insert_query),
                new_rows.to_dict(orient='records')
            )
            logging.info(f"Inserted {len(new_rows)} new rows successfully.")
        except Exception as e:
            logging.error(f"Error inserting new rows: {e}")
else:
    logging.info("No new rows to insert.")

logging.info("Data insertion completed.")