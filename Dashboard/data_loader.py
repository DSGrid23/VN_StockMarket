import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy import create_engine
import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL connection string
conn_str = os.getenv('DATABASE_RENDER')

# Default columns for stock_data
stock_data_necessary_columns = [
    'trade_date',
    'stock_code',
    'listed_shares',
    'shares_outstanding',
    'reference_price',
    'ceiling_price',
    'floor_price',
    'opening_price',
    'closing_price',
    'highest_price',
    'lowest_price',
    'price_change',
    'price_change_percentage',
    'market_capitalization',
    'matched_orders_volume',
    'matched_orders_value',
    'agreements_volume',
    'agreements_value',
    'total_trading_volume',
    'total_trading_value'
]
stock_index_necessary_columns = [
    'trading_date',
    'stock_code',
    'closing_price',
    'price_change',
    'price_change_percentage',
]

columns_map = {
    "stock_data": stock_data_necessary_columns,
    "stock_index": stock_index_necessary_columns,
}

@st.cache_data
def load_all_tables(columns_map=columns_map):
  
    tables = ["stock_data", "stock_info", "financial_metrics", "stock_index"]
    data_frames = {}

    with ThreadPoolExecutor() as executor:
        future_to_table = {
            executor.submit(load_data, table, columns_map.get(table, None) if columns_map else None): table 
            for table in tables
        }
        for future in as_completed(future_to_table):
            table = future_to_table[future]
            try:
                data_frames[table] = future.result()
            except Exception as e:
                st.error(f"Error loading {table}: {e}")
                data_frames[table] = pd.DataFrame()

    return data_frames

@st.cache_data
def load_data(table_name, columns=None):
   
    engine = create_engine(conn_str)
    # Build SQL query
    columns_query = ", ".join(columns) if columns else "*"
    query = f"SELECT {columns_query} FROM {table_name}"

    # Open a connection and execute the query
    with engine.connect() as connection:
        return pd.read_sql(query, connection)

@st.cache_data
def load_stock_data(columns=None):
    """
    Loads stock data from the 'stock_data' table.
    :param columns: List of columns to select (optional).
    :return: A Pandas DataFrame containing the stock data.
    """
    return load_data("stock_data", columns if columns else stock_data_necessary_columns)
@st.cache_data
def load_article():
    try:
        load_dotenv()
        conn_str = os.getenv('DATABASE_RENDER')

        engine = create_engine(conn_str)

        # Fetch data from the table
        query = f"SELECT * FROM article;"
        with engine.connect() as connection:
            df = pd.read_sql(query, connection)
        df['date'] = pd.to_datetime(df['date'])
        
        return df
    except Exception as e:
        print(e)