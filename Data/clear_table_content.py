import sys
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

def clear_table_content(table_name):
    """
    Clear all data from a table in the database without deleting the table itself.
    :param table_name: Name of the table to clear content from.
    """
    try:
        load_dotenv()
        conn_str = os.getenv('DATABASE_RENDER')
        engine = create_engine(conn_str)

        # Clear the content of the table
        with engine.connect() as connection:
            connection.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY;")
        print(f"All data from table '{table_name}' has been cleared successfully.")

    except Exception as e:
        print(f"An error occurred while clearing data from table '{table_name}': {e}")

if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage: python clear_table_content.py [table_name]")
        sys.exit(1)

    table_name = sys.argv[1]
    clear_table_content(table_name)
