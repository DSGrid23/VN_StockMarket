import sys
import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

def table_to_csv(table_name):
    """
    Export a database table to a CSV file.
    :param table_name: Name of the database table (also the name of the CSV file).
    """
    try:
        load_dotenv()
        conn_str = os.getenv('DATABASE_RENDER')

        engine = create_engine(conn_str)

        # Fetch data from the table
        query = f"SELECT * FROM {table_name};"
        with engine.connect() as connection:
            df = pd.read_sql(query, connection)

        # Export to CSV
        csv_file = f"{table_name}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8')
        print(f"Data from table '{table_name}' has been exported to '{csv_file}' successfully.")

    except Exception as e:
        print(f"An error occurred while exporting table '{table_name}' to CSV: {e}")

if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage: python table_to_csv.py [table_name]")
        sys.exit(1)

    table_name = sys.argv[1]
    table_to_csv(table_name)

