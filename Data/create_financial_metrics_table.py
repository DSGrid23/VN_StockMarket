import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
load_dotenv()

# PostgreSQL connection string
conn_str = os.getenv('DATABASE_RENDER')
engine = create_engine(conn_str)

create_table_query = """
    CREATE TABLE IF NOT EXISTS financial_metrics (
        stock_code VARCHAR(20),
        date DATE,
        foreign_buy NUMERIC,
        percent_foreign_ownership NUMERIC,
        cash_dividend NUMERIC,
        dividend_yield NUMERIC,
        beta NUMERIC,
        eps NUMERIC,
        pe NUMERIC,
        forward_pe NUMERIC,
        bvps NUMERIC,
        pb NUMERIC,
        PRIMARY KEY (stock_code, date)
    );
    """
with engine.connect() as connection:
    connection.execute(text(create_table_query))