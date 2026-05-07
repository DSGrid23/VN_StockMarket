from datetime import datetime, timedelta
import gc
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Result
import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

load_dotenv()

conn_str = "postgresql://stock_data_i36c_user:YLMLHhfjF7oIdi3SMzexVaobFuaL37Dc@dpg-csro9ppu0jms73e1epb0-a.singapore-postgres.render.com/stock_data_i36c"
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

# Fetch the stock codes from the database
def fetch_stock_codes():
    try:
        with engine.connect() as connection:
            query = text("SELECT code FROM stock_info")
            result = connection.execute(query)
            result = Result.mappings(result)
            return [row['code'] for row in result]
    except Exception as e:
        print(f"Error fetching stock codes: {e}")
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
    except requests.exceptions.RequestException as e:
        print(f"Failed to get the data for {code}. Response status: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error when parsing data for {code}: {e}")
        return None

# def insert_data_to_db(df, table_name):
#     engine = create_engine(conn_str)
#     try:
#         with engine.connect() as connection:
#             # connection.execute("SELECT 1")
#             for _, row in df.iterrows():
#                 query = text("""
#                     SELECT COUNT(*) FROM stock_data 
#                     WHERE trade_date = :trade_date AND stock_code = :stock_code
#                 """)
#                 result = connection.execute(query, {'trade_date': row['trade_date'], 'stock_code': row['stock_code']})
#                 count = result.scalar()

#                 if count == 0:
#                     row.to_frame().T.to_sql("stock_data", con=connection, if_exists="append", index=False, chunksize=1000)
#                     print(row.to_frame())
#                     # print(f"Added entry for {row['trade_date']} and {row['stock_code']}")
#                 # else:
#                     # print(f"Duplicate entry for {row['trade_date']} and {row['stock_code']}, skipping.")
#     except Exception as e:
#         print(f"Error inserting data to {table_name}: {e}")


def insert_data_to_db(df, table_name):
    engine = create_engine(conn_str)
    try:
        with engine.connect() as connection:
            for _, row in df.iterrows():
                # Kiểm tra nếu bản ghi chưa tồn tại
                query = text("""
                    SELECT COUNT(*) FROM stock_data 
                    WHERE trade_date = :trade_date AND stock_code = :stock_code
                """)
                result = connection.execute(query, {'trade_date': row['trade_date'], 'stock_code': row['stock_code']})
                count = result.scalar()

                if count == 0:
            
                    insert_query = text("""
                        INSERT INTO stock_data (
                            trade_date, stock_code, listed_shares, shares_outstanding, reference_price,
                            ceiling_price, floor_price, total_trading_volume, total_trading_value, market_capitalization,
                            opening_price, closing_price, highest_price, lowest_price, difference, average_price,
                            adjusted_closing_price, price_change, price_change_percentage, average_buy_price,
                            average_sell_price, buy_limit, sell_limit, matched_orders_volume, matched_orders_value,
                            total_orders_placed_buy, total_orders_placed_sell, total_volume_placed_buy,
                            total_volume_placed_sell, agreements_volume, agreements_value
                        )
                        VALUES (
                            :trade_date, :stock_code, :listed_shares, :shares_outstanding, :reference_price,
                            :ceiling_price, :floor_price, :total_trading_volume, :total_trading_value, :market_capitalization,
                            :opening_price, :closing_price, :highest_price, :lowest_price, :difference, :average_price,
                            :adjusted_closing_price, :price_change, :price_change_percentage, :average_buy_price,
                            :average_sell_price, :buy_limit, :sell_limit, :matched_orders_volume, :matched_orders_value,
                            :total_orders_placed_buy, :total_orders_placed_sell, :total_volume_placed_buy,
                            :total_volume_placed_sell, :agreements_volume, :agreements_value
                        )
                    """)
                    # Chạy câu truy vấn insert
                    connection.execute(insert_query, {
                        'trade_date': row['trade_date'],
                        'stock_code': row['stock_code'],
                        'listed_shares': row['listed_shares'],
                        'shares_outstanding': row['shares_outstanding'],
                        'reference_price': row['reference_price'],
                        'ceiling_price': row['ceiling_price'],
                        'floor_price': row['floor_price'],
                        'total_trading_volume': row['total_trading_volume'],
                        'total_trading_value': row['total_trading_value'],
                        'market_capitalization': row['market_capitalization'],
                        'opening_price': row['opening_price'],
                        'closing_price': row['closing_price'],
                        'highest_price': row['highest_price'],
                        'lowest_price': row['lowest_price'],
                        'difference': row['difference'],
                        'average_price': row['average_price'],
                        'adjusted_closing_price': row['adjusted_closing_price'],
                        'price_change': row['price_change'],
                        'price_change_percentage': row['price_change_percentage'],
                        'average_buy_price': row['average_buy_price'],
                        'average_sell_price': row['average_sell_price'],
                        'buy_limit': row['buy_limit'],
                        'sell_limit': row['sell_limit'],
                        'matched_orders_volume': row['matched_orders_volume'],
                        'matched_orders_value': row['matched_orders_value'],
                        'total_orders_placed_buy': row['total_orders_placed_buy'],
                        'total_orders_placed_sell': row['total_orders_placed_sell'],
                        'total_volume_placed_buy': row['total_volume_placed_buy'],
                        'total_volume_placed_sell': row['total_volume_placed_sell'],
                        'agreements_volume': row['agreements_volume'],
                        'agreements_value': row['agreements_value']
                    })
                    check_query = text("""
                        SELECT COUNT(*) FROM stock_data
                        WHERE trade_date = :trade_date AND stock_code = :stock_code
                    """)
                    check_result = connection.execute(check_query, {'trade_date': row['trade_date'], 'stock_code': row['stock_code']})
                    check_count = check_result.scalar()

                    if check_count > 0:
                        print(f"Data for {row['trade_date']} and {row['stock_code']} confirmed inserted into the database.")
                    else:
                        print(f"Failed to insert data for {row['trade_date']} and {row['stock_code']}.")
                    # print(f"Added entry for {row['trade_date']} and {row['stock_code']}")
                else:
                    print(f"Duplicate entry for {row['trade_date']} and {row['stock_code']}, skipping.")
    except Exception as e:
        print(f"Error inserting data to {table_name}: {e}")

def process_stock_data(ticker, from_date, to_date):
    print(f"Processing stock code {ticker}...")
    df = download_data_to_dataframe(ticker, from_date, to_date)
    if df is not None:
        try:
            df = df.drop(df.columns[[29, 26]], axis=1)
            df.columns = new_column_names
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%d/%m/%Y').dt.strftime('%Y-%m-%d')
            df.insert(1, 'stock_code', ticker)
            df.replace("-", None, inplace=True)
            insert_data_to_db(df, table_name="stock_data")

            print(f"Inserted data for {ticker} successfully!")
        except Exception as e:
            print(f"Error processing data for {ticker}: {e}")
        finally:
            # Free up memory
            del df
            gc.collect()
    else:
        print(f"No data available for {ticker}.")

def update_database(ticker_list, from_date, to_date):
    for ticker in ticker_list:
        process_stock_data(ticker, from_date, to_date)

if __name__ == "__main__":
    from_date = (datetime.today() - timedelta(days=7)).strftime('%Y-%m-%d')
    to_date = datetime.today().strftime('%Y-%m-%d')
    print(f"From date: {from_date}, To date: {to_date}")
    
    ticker_list = fetch_stock_codes()
    print(f"Fetched stock codes: {ticker_list[0:10]}")
    # Kiểm tra kết nối
    with engine.connect() as connection:
        print("Connection successful!")

    update_database(ticker_list, from_date, to_date)
    gc.collect()
