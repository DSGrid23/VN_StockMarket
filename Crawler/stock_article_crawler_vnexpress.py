import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from datetime import datetime
import time
from newspaper import Article
import urllib.request
from urllib.error import URLError
from sqlalchemy.dialects.postgresql import insert
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Connect to PostgreSQL database
engine = create_engine('postgresql+psycopg2://caokhoi:m6ikFt3TKwnkV75fNZ2FBdKiEHKEu1sN@dpg-cs87v7m8ii6s73c5m19g-a.singapore-postgres.render.com:5432/stock_data_01')

def fetch_page(url, retries=3, delay=3):
    for attempt in range(retries):
        try:
            page = urllib.request.urlopen(url, timeout=10)
            return page
        except URLError as e:
            logging.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
            time.sleep(delay)
    return None

def get_links_in_page_vnexpress(url):
    try:
        page = fetch_page(url)
        if page is None:
            logging.error(f"Failed to fetch page {url}")
            return []

        soup = BeautifulSoup(page, 'html.parser')
        sections = soup.find_all('section', attrs={'class': 'section section_container mt15'})

        links = []
        for section in sections:
            titles = section.find_all('h2', attrs={'class': 'title-news'})
            for title in titles:
                a = title.find('a')
                if a:
                    link = a.get('href')
                    title_text = a.get('title')
                    if title_text and link:
                        links.append({'title': title_text, 'link': link})
                        logging.info(f"Found title: {title_text} - Link: {link}")
        return links
    except Exception as e:
        logging.error(f"Error parsing links from page {url}: {e}")
        return []

def get_links():
    news_list = []
    urls = [f'https://vnexpress.net/kinh-doanh/chung-khoan-p{i}' for i in range(1, 21)]

    for url in urls:
        try: 
            news_list.extend(get_links_in_page_vnexpress(url))
        except Exception as e:
            logging.error(f"Error fetching links from {url}: {e}")

    df = pd.DataFrame(news_list).drop_duplicates(subset=['link']).reset_index(drop=True)
    return df

def normalize_date(date_str):
    try:
        date = date_str.split(',')[1].strip()
        parsed_date = pd.to_datetime(date, format='%d/%m/%Y')
        return parsed_date.strftime('%Y-%m-%d')
    except Exception as e:
        logging.error(f"Error normalizing date: {date_str}, {e}")
        return None

def crawl_by_url(url, retries=3, backoff_factor=0.3):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'
    }
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, allow_redirects=False)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # date = normalize_date(soup.find('span', class_='date').text) if soup.find('span', class_='date') else None
                if soup.find('span', class_='date'):
                    date = soup.find('span', class_='date').text
                    date = normalize_date(date)
                else :
                    date = None

                article = Article(url, language='vi')
                article.set_html(response.text)
                article.download(input_html=response.text)
                article.parse()

                content = str(article.text).strip()
                return date, content
            else:
                logging.error(f"Failed to crawl {url}, status code: {response.status_code}")

        except requests.exceptions.RequestException as e:
            logging.error(f"Error during crawling {url}: {e}")
            time.sleep(backoff_factor * (2 ** attempt))
    return None, None

def process(df):

    for index, row in df.iterrows():
        logging.info(f"Processing {index + 1}/{df.shape[0]}: {row['link']}")
        date, content = crawl_by_url(row['link'])
        df.at[index, 'date'] = date
        df.at[index, 'content'] = content
    return df

def get_existing_articles():
    try:
        query = "SELECT title, date FROM article"
        with engine.connect() as connection:
            result = connection.execute(query)
            existing_articles = set((row['title'], row['date']) for row in result)
        return existing_articles
    except Exception as e:
        logging.error(f"Error fetching existing articles: {e}")
        return set()


def filter_new_articles(df):
    try:
        existing_articles = get_existing_articles()
        df['date'] = pd.to_datetime(df['date']).dt.date
        df['title'] = df['title'].str.strip()
        new_df = df[~df[['title', 'date']].apply(tuple, axis=1).isin(existing_articles)]
        return new_df
    except Exception as e:
        logging.error(f"Error filtering new articles: {e}")
        return pd.DataFrame()
    
def insert_articles_to_db(new_articles_df):
    try:
        with engine.connect() as connection:
            for _, row in new_articles_df.iterrows():
                insert_query = """
                INSERT INTO article (title, link, content, date)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (title, date) DO NOTHING
                """
                try:
                    connection.execute(insert_query, (row['title'], row['link'], row['content'], row['date']))
                except Exception as e:
                    print(f"Error inserting article '{row['title']}' into the database: {e}")
        print("Insertion completed with row-by-row conflict handling.")
    except Exception as e:
        print(f"Error in database insertion process: {e}")

def count_articles():
    with engine.connect() as connection:
        result = connection.execute("SELECT COUNT(*) FROM article")
        count = result.scalar()
    return count


def main():
    try:
        initial_count = count_articles()
        print(initial_count)
        df = get_links()
        df['content'] = ''
        df['date'] = ''

        # Process a sample of the DataFrame
        df = process(df)
        df.dropna(subset=['content', 'date'], inplace=True)
        print(df['date'])


        new_df = filter_new_articles(df)

        if not new_df.empty:
            insert_articles_to_db(new_df)
            logging.info("Insertion completed.")

            final_count = count_articles()
            logging.info(f"Final article count: {final_count}")

            inserted_count = final_count - initial_count
            logging.info(f"Number of articles inserted: {inserted_count}")


        else:
            logging.info("No new articles to insert.")
    except Exception as e:
        logging.error(f"Error in main execution: {e}")

if __name__ == "__main__":
    main()
    # str = "Thứ năm, 26/9/2024, 16:02 (GMT+7)"
    # print(normalize_date(str))
