from datetime import datetime, timedelta
import gc
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Result
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from io import StringIO

load_dotenv()

conn_str = "postgresql://vietstock_db_user:ucuQzvLk2ISHZHeIK6rENuPwhfXnDOdv@dpg-d7u18n1j2pic739dhrig-a.oregon-postgres.render.com/vietstock_db"

engine = create_engine(conn_str)

# =========================
# LIST TABLES
# =========================
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """))

    tables = [row[0] for row in result]

    print("Tables in database:")
    for table in tables:
        print(table)

# =========================
# COLUMN NAMES
# =========================
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

# =========================
# CLEAN VALUE
# =========================
def clean_value(v):

    if pd.isna(v):
        return None

    if isinstance(v, str):

        v = v.strip()

        if v == "" or v == "-":
            return None

        # remove thousand separator
        v = v.replace(".", "")

        # decimal comma -> dot
        v = v.replace(",", ".")

    try:
        if "." in str(v):
            return float(v)

        return int(v)

    except:
        return v

# =========================
# FETCH STOCK CODES
# =========================
def fetch_stock_codes():

    try:
        with engine.connect() as connection:

            query = text("SELECT code FROM stock_info")

            result = connection.execute(query)

            result = Result.mappings(result)

            stock_codes = [row['code'] for row in result]

            print(stock_codes)

            return stock_codes

    except Exception as e:

        print(f"Error fetching stock codes: {e}")

        return []

# =========================
# DOWNLOAD DATA
# =========================
def download_data_to_dataframe(code, from_date, to_date, page_index=1, page_size=10):

    url = f"https://finance.vietstock.vn/data/ExportTradingResult?Code={code}&OrderBy=&OrderDirection=desc&PageIndex={page_index}&PageSize={page_size}&FromDate={from_date}&ToDate={to_date}&ExportType=excel&Cols=KLNY%2CKLCPDLH%2CGTC%2CT%2CS%2CTKLGD%2CTGTGD%2CVHTT%2CMC%2CTGG%2CLDM%2CDC%2CTGPTG%2CLDB%2CCN%2CBQM%2CLDMB%2CTN%2CBQB%2CKLDM%2CGYG%2CDM%2CKLDB%2CBQ%2CDB%2CKLDMB%2CGDC%2CKLGDKL%2CGTGDKL%2CKLGDTT%2CGTGDTT&ExchangeID=5"

    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://finance.vietstock.vn/'
    }

    try:

        response = requests.get(url, headers=headers)

        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        tables = soup.find_all("table")

        # FIX FutureWarning
        df = pd.read_html(StringIO(str(tables[1])))[0]

        return df

    except requests.exceptions.RequestException as e:

        print(f"Failed to get data for {code}: {e}")

        return None

    except Exception as e:

        print(f"Unexpected error for {code}: {e}")

        return None

# =========================
# INSERT DATA
# =========================
def insert_data_to_db(df, table_name):

    try:

        # AUTO COMMIT
        with engine.begin() as connection:

            for _, row in df.iterrows():

                # check duplicate
                check_query = text("""
                    SELECT COUNT(*)
                    FROM stock_data
                    WHERE trade_date = :trade_date
                    AND stock_code = :stock_code
                """)

                result = connection.execute(
                    check_query,
                    {
                        'trade_date': row['trade_date'],
                        'stock_code': row['stock_code']
                    }
                )

                count = result.scalar()

                if count > 0:

                    #print(f"Duplicate entry: {row['trade_date']} - {row['stock_code']}")

                    continue

                insert_query = text("""
                    INSERT INTO stock_data (
                        trade_date,
                        stock_code,
                        listed_shares,
                        shares_outstanding,
                        reference_price,
                        ceiling_price,
                        floor_price,
                        total_trading_volume,
                        total_trading_value,
                        market_capitalization,
                        opening_price,
                        closing_price,
                        highest_price,
                        lowest_price,
                        difference,
                        average_price,
                        adjusted_closing_price,
                        price_change,
                        price_change_percentage,
                        average_buy_price,
                        average_sell_price,
                        buy_limit,
                        sell_limit,
                        matched_orders_volume,
                        matched_orders_value,
                        total_orders_placed_buy,
                        total_orders_placed_sell,
                        total_volume_placed_buy,
                        total_volume_placed_sell,
                        agreements_volume,
                        agreements_value
                    )
                    VALUES (
                        :trade_date,
                        :stock_code,
                        :listed_shares,
                        :shares_outstanding,
                        :reference_price,
                        :ceiling_price,
                        :floor_price,
                        :total_trading_volume,
                        :total_trading_value,
                        :market_capitalization,
                        :opening_price,
                        :closing_price,
                        :highest_price,
                        :lowest_price,
                        :difference,
                        :average_price,
                        :adjusted_closing_price,
                        :price_change,
                        :price_change_percentage,
                        :average_buy_price,
                        :average_sell_price,
                        :buy_limit,
                        :sell_limit,
                        :matched_orders_volume,
                        :matched_orders_value,
                        :total_orders_placed_buy,
                        :total_orders_placed_sell,
                        :total_volume_placed_buy,
                        :total_volume_placed_sell,
                        :agreements_volume,
                        :agreements_value
                    )
                """)

                data = {
                    col: (None if pd.isna(row[col]) else row[col])
                    for col in df.columns
                }

                try:

                    connection.execute(insert_query, data)

                    #print(f"Inserted: {row['trade_date']} - {row['stock_code']}")

                except Exception as e:

                    print("FAILED ROW:")
                    print(data)
                    print(e)

    except Exception as e:

        print(f"Error inserting data into {table_name}: {e}")

# =========================
# PROCESS STOCK
# =========================
def process_stock_data(ticker, from_date, to_date):

    print(f"Processing {ticker}...")

    df = download_data_to_dataframe(
        ticker,
        from_date,
        to_date
    )

    if df is None:

        print(f"No data for {ticker}")

        return

    try:

        # remove unnecessary columns
        df = df.drop(df.columns[[29, 26]], axis=1)

        # rename columns
        df.columns = new_column_names

        # date format
        df['trade_date'] = pd.to_datetime(
            df['trade_date'],
            format='%d/%m/%Y'
        ).dt.strftime('%Y-%m-%d')

        # insert stock code
        df.insert(1, 'stock_code', ticker)

        # replace dash
        df.replace("-", None, inplace=True)

        # clean dataframe
        df = df.map(clean_value)

        # NaN -> None
        df = df.where(pd.notnull(df), None)

        print(df.head())

        insert_data_to_db(df, "stock_data")

        print(f"Finished {ticker}")

    except Exception as e:

        print(f"Error processing {ticker}: {e}")

    finally:

        del df

        gc.collect()

# =========================
# UPDATE DATABASE
# =========================
def update_database(ticker_list, from_date, to_date):

    for ticker in ticker_list:

        process_stock_data(
            ticker,
            from_date,
            to_date
        )

# =========================
# MAIN
# =========================
if __name__ == "__main__":

    # 2 years ago
    from_date = (
        datetime.today() - timedelta(days=365*2)
    ).strftime('%Y-%m-%d')

    to_date = datetime.today().strftime('%Y-%m-%d')

    print(f"From: {from_date}")
    print(f"To: {to_date}")

    stock_info_data = pd.read_csv("stock_info.csv")

    print(stock_info_data.head())

    ticker_list = stock_info_data['code'].tolist()

    print(f"Total tickers: {len(ticker_list)}")

    print(ticker_list[:10])

    # test connection
    with engine.connect() as connection:

        print("Database connection successful!")

    update_database(
        ticker_list,
        from_date,
        to_date
    )

    gc.collect()