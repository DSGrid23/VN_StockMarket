import pandas as pd
from sqlalchemy import create_engine
import logging

logging.basicConfig( level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

new_conn_str = 'postgresql://stock_data_i36c_user:YLMLHhfjF7oIdi3SMzexVaobFuaL37Dc@dpg-csro9ppu0jms73e1epb0-a.singapore-postgres.render.com/stock_data_i36c'
new_engine = create_engine(new_conn_str)


def create_table_from_df(table_name, df, engine):
    try:

        df.to_sql(table_name, con=engine, if_exists='append', index=False)
        logging.info(f"Table {table_name} has been created/updated successfully.")

    except Exception as e:
        logging.error(f"Error creating/updating table {table_name}: {e}")

def update_table_from_csv(table_name, csv_file, engine):
    try:
        df = pd.read_csv(csv_file)
        logging.info(f"Loaded data from {csv_file} with {len(df)} rows.")

        create_table_from_df(table_name, df, engine)

    except FileNotFoundError:
        logging.error(f"File not found: {csv_file}")

    except Exception as e:
        logging.error(f"Error updating table {table_name} with data from {csv_file}: {e}")

# csv_files = ["stock_data.csv", "stock_index.csv", "stock_info.csv", "article.csv", "financial_metrics.csv"]
# table_names = ["stock_data", "stock_index", "stock_info", "article", "financial_metrics"] 

csv_files = ["financial_metrics_1.csv"]
table_names = ["financial_metrics"]

for csv_file, table_name in zip(csv_files, table_names):
    logging.info(f"Starting update for table {table_name} from file {csv_file}.")
    update_table_from_csv(table_name, csv_file, new_engine)
    logging.info(f"Finished update for table {table_name}.")

logging.info("All updates completed.")

