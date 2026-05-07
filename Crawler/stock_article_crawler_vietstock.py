import requests
import pandas as pd
import logging
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import pytz
import time
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

conn_str = 'postgresql://stock_data_i36c_user:YLMLHhfjF7oIdi3SMzexVaobFuaL37Dc@dpg-csro9ppu0jms73e1epb0-a.singapore-postgres.render.com/stock_data_i36c'
engine = create_engine(conn_str)

url = 'https://vietstock.vn/_Partials/GetStockNewsByMarketPaging'
headers = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Content-Type': 'application/json; charset=UTF-8',
    'Origin': 'https://vietstock.vn',
    'Referer': 'https://vietstock.vn/chu-de/1-8/tat-ca.htm',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
    'X-Requested-With': 'XMLHttpRequest'
}

def get_existing_articles():
    try:
        query = "SELECT title, date FROM article"
        with engine.connect() as connection:
            result = connection.execute(query)
            return set((row['title'], row['date']) for row in result)
    except SQLAlchemyError as e:
        logging.error(f"Error retrieving existing articles from the database: {e}")
        return set()  


def fetch_data():
    titles, contents, links, publish_times, article_ids = [], [], [], [], []
    current_page = 1
    total_pages = None
    stop_fetching = False 

    while total_pages is None or current_page <= 10:
        data = {
            "item": 15,
            "martket": "1",
            "row": current_page
        }

        response = requests.post(url, headers=headers, json=data)

        try:
            response_data = response.json()
        except ValueError:
            logging.error(f"Skipping page {current_page}: Response is not in JSON format.")
            current_page += 1
            time.sleep(1)
            continue

        if total_pages is None:
            total_pages = response_data.get("TotalPage", 1)
            logging.info(f"Total pages to fetch: {total_pages}")


        if 'Data' not in response_data or not response_data['Data']:
            logging.info("No more data found.")
            break

        # Process each news item in the response
        for item in response_data['Data']:
            link = f"https://vietstock.vn{item['URL']}"

            # Check if the URL contains a year less than 2022
            year_match = re.search(r'\b(19[0-9]{2}|20[0-2][0-9])\b', link)
            if year_match and int(year_match.group()) < 2023:
                logging.info(f"Encountered a URL with a year < 2022: {link}")
                stop_fetching = True ,
                break  # Stop processing further items in the current page
            

            title = item['Title']
            article_id = item['ArticleID']

            # Content - parse HTML content
            content = BeautifulSoup(item['Content'], 'html.parser').get_text(strip=True)

            # Publish Time
            timestamp = int(re.search(r"\d+", item['PublishTime']).group())
            publish_time = datetime.fromtimestamp(timestamp / 1000, tz=pytz.timezone('Asia/Bangkok')).strftime("%Y-%m-%d")

            titles.append(title)
            contents.append(content)
            links.append(link)
            publish_times.append(publish_time)
            article_ids.append(article_id)

        logging.info(f"Fetched page {current_page}")
        current_page += 1
        time.sleep(1)  

        if stop_fetching:
            logging.info("Stopped fetching due to encountering a URL with a year < 2022.")
            break

    return pd.DataFrame({
        'title': titles,
        'link': links,
        'content': contents,
        'date': publish_times,
    })

def filter_new_articles(news_df):
    try:
        existing_articles = get_existing_articles()
        news_df['title'] = news_df['title'].str.strip()
        new_articles_df = news_df[~news_df[['title', 'date']].apply(tuple, axis=1).isin(existing_articles)]
        return new_articles_df
    except Exception as e:
        logging.error(f"Error filtering new articles: {e}")
        return news_df

# def insert_articles_to_db(new_articles_df):
#     try:

#         with engine.connect() as connection:
#             for _, row in new_articles_df.iterrows():
#                 insert_query = """
#                 INSERT INTO article (title, link, content, date)
#                 VALUES (%s, %s, %s, %s)
#                 """
#                 try:
#                     connection.execute(insert_query, (row['title'], row['link'], row['content'], row['date']))
#                 except SQLAlchemyError as e:
#                     logging.error(f"Error inserting article '{row['title']}': {e}")
#     except SQLAlchemyError as e:
#         logging.error(f"Database insertion error: {e}")

def insert_articles_to_db(new_articles_df):

    engine = create_engine(conn_str)
    try:
        with engine.connect() as connection:
            insert_query = """
            INSERT INTO article (title, link, content, date)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (title, date) DO NOTHING
            """
            values = list(new_articles_df[['title', 'link', 'content', 'date']].itertuples(index=False, name=None))
            connection.execute(insert_query, values)
    except SQLAlchemyError as e:
        logging.error(f"Database insertion error: {e}")


initial_count_query = "SELECT COUNT(*) FROM article"

def main():
    try:

        
        with engine.connect() as conn:
            initial_count = conn.execute(initial_count_query).scalar()
            logging.info(f"Initial article count: {initial_count}")

        news_df = fetch_data()
        new_articles_df = filter_new_articles(news_df)
        logging.info(f"New articles to insert: {new_articles_df.shape[0]}")

        if not new_articles_df.empty:
            insert_articles_to_db(new_articles_df)
            logging.info(f"Insert complete.")

            time.sleep(10)
        else:
            logging.info("No new articles to insert.")
    except Exception as e:
        logging.error(f"An error occurred in the main process: {e}")

if __name__ == "__main__":
    main()
