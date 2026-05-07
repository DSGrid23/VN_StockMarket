from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
load_dotenv()

# PostgreSQL connection string
conn_str = os.getenv('DATABASE_RENDER')
engine = create_engine(conn_str)

create_table_query = """
CREATE TABLE IF NOT EXISTS stock_data (
    trade_date DATE,
    stock_code VARCHAR(50),
    listed_shares BIGINT,
    shares_outstanding BIGINT,
    reference_price DECIMAL(10, 2),
    ceiling_price DECIMAL(10, 2),
    floor_price DECIMAL(10, 2),
    total_trading_volume BIGINT,
    total_trading_value DECIMAL(15, 2),
    market_capitalization DECIMAL(15, 2),
    opening_price DECIMAL(10, 2),
    closing_price DECIMAL(10, 2),
    highest_price DECIMAL(10, 2),
    lowest_price DECIMAL(10, 2),
    difference DECIMAL(10, 2),
    average_price DECIMAL(10, 2),
    adjusted_closing_price DECIMAL(10, 2),
    price_change DECIMAL(10, 2),
    price_change_percentage DECIMAL(5, 2),
    average_buy_price DECIMAL(10, 2),
    average_sell_price DECIMAL(10, 2),
    buy_limit BIGINT,
    sell_limit BIGINT,
    matched_orders_volume BIGINT,
    matched_orders_value BIGINT,
    total_orders_placed_buy BIGINT,
    total_orders_placed_sell BIGINT,
    total_volume_placed_buy BIGINT,
    total_volume_placed_sell BIGINT,
    agreements_volume DECIMAL(15, 2),
    agreements_value DECIMAL(15, 2),
    PRIMARY KEY (trade_date, stock_code)
);
"""

with engine.connect() as connection:
    connection.execute(create_table_query)
