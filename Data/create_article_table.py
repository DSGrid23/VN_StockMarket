from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
load_dotenv()

# PostgreSQL connection string
conn_str = os.getenv('DATABASE_RENDER')
engine = create_engine(conn_str)

create_article_table_query = """
CREATE TABLE IF NOT EXISTS article (
    title VARCHAR(255),
    link TEXT,
    content TEXT,
    date DATE,
    PRIMARY KEY (title, date)
);
"""

# Execute the query to create the table
with engine.connect() as connection:
    connection.execute(create_article_table_query)

print("Table 'article' created successfully.")

