from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
load_dotenv()

# PostgreSQL connection string
conn_str = os.getenv('DATABASE_RENDER')
engine = create_engine(conn_str)

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