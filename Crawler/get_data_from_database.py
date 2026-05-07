import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import text

from sqlalchemy.engine import Result

# Database connection string (provided)
conn_str = 'postgresql://stock_data_i36c_user:YLMLHhfjF7oIdi3SMzexVaobFuaL37Dc@dpg-csro9ppu0jms73e1epb0-a.singapore-postgres.render.com/stock_data_i36c'
engine = create_engine(conn_str)

# Connect to the database and retrieve all table names
with engine.connect() as connection:
    # Retrieve all table names
    tables_query = text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    result = connection.execute(tables_query)
    result = Result.mappings(result)
    table_names = [row['table_name'] for row in result]

# Fetch data from each table and save to CSV
for table in table_names:
    try:
        # Read table into DataFrame
        df = pd.read_sql(f"SELECT * FROM {table}", con=engine)
        
        # Save to CSV file
        df.to_csv(f"{table}.csv", index=False)
        print(f"Data from table {table} has been saved to {table}.csv")
    
    except Exception as e:
        print(f"Error exporting table {table}: {e}")
