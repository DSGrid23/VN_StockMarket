import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import time
import pytz
from newspaper import Article
import urllib.request
from urllib.error import URLError
import logging
from airflow import DAG
from airflow.operators.python import PythonOperator
import os
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL connection string
conn_str = os.getenv('DATABASE_RENDER')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Connect to PostgreSQL database
engine = create_engine(conn_str)

# Shared helper functions
def fetch_page(url, retries=3, delay=3):
    for attempt in range(retries):
        try:
            page = urllib.request.urlopen(url, timeout=10)
            return page
        except URLError as e:
            logging.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
            time.sleep(delay)
    return None

def get_existing_links():
    """Fetch existing links from the database."""
    try:
        query = "SELECT link FROM article"
        with engine.connect() as connection:
            result = connection.execute(query)
            existing_links = set(row['link'] for row in result)
        return existing_links
    except Exception as e:
        logging.error(f"Error fetching existing links: {e}")
        return set()

def insert_articles_to_db(new_articles_df):
    """Insert new articles into the database."""
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

# VnExpress crawler functions
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

def get_links_vnexpress():
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


def process_vnexpress(df):
    for index, row in df.iterrows():
        logging.info(f"Processing {index + 1}/{df.shape[0]}: {row['link']}")
        date, content = crawl_by_url(row['link'])
        df.at[index, 'date'] = date
        df.at[index, 'content'] = content
    return df

def vnexpress_crawler():
    try:
        logging.info("Starting VnExpress crawler...")
        # Step 1: Fetch links from VnExpress
        df = get_links_vnexpress()
        df = df.drop_duplicates(subset=['link']).reset_index(drop=True)
        df['content'] = ''
        df['date'] = ''
        
        # Step 2: Check for existing links in the database
        existing_links = get_existing_links()
        df = df[~df['link'].isin(existing_links)].reset_index(drop=True)
        
        logging.info(f"Found {df.shape[0]} new articles to process.")
        
        if df.empty:
            logging.info("No new VnExpress articles to process.")
            return
        # Step 3: Process each article
        df = process_vnexpress(df)
        df = df.dropna(subset=['date', 'content'])
        if not df.empty:
            insert_articles_to_db(df)
        logging.info("VnExpress crawler completed.")
    except Exception as e:
        logging.error(f"Error in VnExpress crawler: {e}")

# Vietstock crawler functions 
url = 'https://vietstock.vn/_Partials/GetStockNewsByMarketPaging'
headers = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Content-Type': 'application/json; charset=UTF-8',
    'Origin': 'https://vietstock.vn',
    'Referer': 'https://vietstock.vn/chu-de/1-8/tat-ca.htm',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
    'X-Requested-With': 'XMLHttpRequest'
}

def fetch_Vietstock_data():
    titles, contents, links, publish_times, article_ids = [], [], [], [], []
    current_page = 1
    total_pages = None
    stop_fetching = False 

    while total_pages is None or current_page <= 100:
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
                stop_fetching = True
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
    
def vietstock_crawler():
    try:
        logging.info("Starting Vietstock crawler...")
        new_vietstock_df = fetch_Vietstock_data()
        new_vietstock_df = new_vietstock_df.drop_duplicates(subset=['link']).reset_index(drop=True)
        
        existing_links = get_existing_links()
        new_vietstock_df = new_vietstock_df[~new_vietstock_df['link'].isin(existing_links)].reset_index(drop=True)
        logging.info(f"Found {new_vietstock_df.shape[0]} new articles to insert.")
        
        if new_vietstock_df.empty:
            logging.info("No new Vietstock articles to insert.")
            return
        
        insert_articles_to_db(new_vietstock_df)
        logging.info("Vietstock crawler completed.")
    except Exception as e:
        logging.error(f"Error in Vietstock crawler: {e}")

# Define the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='vnexpress_and_vietstock_crawler',
    default_args=default_args,
    schedule_interval='@daily',
    start_date=datetime(2024, 10, 1, 0, 0),
    catchup=False,
    description='Crawl articles from VnExpress and Vietstock sequentially',
    tags=['vnexpress', 'vietstock', 'crawler']
) as dag:
    vnexpress_task = PythonOperator(
        task_id='vnexpress_crawler_task',
        python_callable=vnexpress_crawler,
    )

    vietstock_task = PythonOperator(
        task_id='vietstock_crawler_task',
        python_callable=vietstock_crawler,
    )

    vnexpress_task >> vietstock_task
