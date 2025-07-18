import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import sys
import re
import importlib
from datetime import datetime, date

# Add the project root to the PATH to locate config module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config # Import config here
importlib.reload(config) # Reload config to ensure latest version

def fetch_page_content(url, headers=None, current_config=None):
    """
    Retrieves the HTML content of a webpage.
    """
    if headers is None:
        headers = current_config.HEADERS if current_config else config.HEADERS
    print(f"Attempting to retrieve content from: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        print(f"Successfully retrieved page {url}")
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving page {url}: {e}")
        return None

def parse_minfin_news(html_content, current_config=None):
    """
    Parses the Ministry of Finance news page and extracts information.
    """
    if not html_content:
        return []
    soup = BeautifulSoup(html_content, 'lxml')
    news_entries = []
    articles = soup.find_all('article', class_=lambda x: x and 'elementor-post' in x.split() and 'elementor-grid-item' in x.split())
    if not articles:
        print("Note: No 'article.elementor-post.elementor-grid-item' found on Ministry of Finance page.")
        return []
    for article in articles:
        title_tag = article.find('h3', class_='elementor-post__title')
        link_tag = None
        if title_tag:
            link_tag = title_tag.find('a', href=True)
        date_tag = article.find('span', class_='elementor-post-date')
        if link_tag and title_tag and date_tag:
            title = title_tag.get_text(strip=True)
            link = link_tag['href']
            date_str = date_tag.get_text(strip=True)
            news_entries.append({
                'title': title, 'url': link, 'date': date_str, 'source': 'Ministry of Finance'
            })
    return news_entries

def parse_aade_news(html_content, current_config=None):
    """
    Parses the AADE press releases page and extracts information.
    """
    if not html_content:
        return []
    soup = BeautifulSoup(html_content, 'lxml')
    news_entries = []
    items = soup.find_all('div', class_='views-row')
    if not items:
        print("Note: No 'div.views-row' found on AADE page.")
        return []
    for item in items:
        date_span = item.find('span', class_='field-content')
        link_tag = item.find('a', class_='category-item-title', href=True)
        title_text_element = item.find('p')
        if date_span and link_tag:
            date_str = date_span.get_text(strip=True)
            title = link_tag.get_text(strip=True) if link_tag else (title_text_element.get_text(strip=True) if title_text_element else "N/A Title")
            link = requests.compat.urljoin(current_config.AADE_NEWS_URL if current_config else config.AADE_NEWS_URL, link_tag['href'])
            news_entries.append({
                'title': title, 'url': link, 'date': date_str, 'source': 'AADE'
            })
    return news_entries

def parse_capital_news(html_content, current_config=None):
    """
    Parses the Capital.gr news page and extracts information.
    """
    if not html_content:
        return []
    soup = BeautifulSoup(html_content, 'lxml')
    news_entries = []
    articles = soup.find_all('div', class_=lambda x: x and 'article' in x.split() and 'snip' in x.split())
    if not articles:
        print("Note: No 'div.article.snip' found on Capital.gr page.")
        return []
    for article in articles:
        title_h2 = article.find('h2', class_='bold')
        link_tag = None
        if title_h2:
            link_tag = title_h2.find('a', href=True)
        date_span = article.find('span', class_='date')
        time_span = article.find('span', class_='time')
        if link_tag and date_span:
            title = link_tag.get_text(strip=True)
            link = requests.compat.urljoin(current_config.CAPITAL_NEWS_URL if current_config else config.CAPITAL_NEWS_URL, link_tag['href'])
            date_str = date_span.get_text(strip=True)
            time_str = time_span.get_text(strip=True) if time_span else "00:00"
            full_date_str = f"{date_str} {time_str}"
            news_entries.append({
                'title': title, 'url': link, 'date': full_date_str, 'source': 'Capital.gr'
            })
    return news_entries

def get_latest_legislative_news(current_config=None, filter_by_current_date=False):
    """
    Collects the latest legislative news and announcements from all sources.
    If filter_by_current_date is True, returns only news from the current date.
    """
    all_news_data = []
    today = date.today()

    cfg = current_config if current_config else config

    minfin_html = fetch_page_content(cfg.MINISTRY_FINANCE_NEWS_URL, headers=cfg.HEADERS, current_config=cfg)
    if minfin_html:
        minfin_data = parse_minfin_news(minfin_html, current_config=cfg)
        if minfin_data:
            print(f"Found {len(minfin_data)} news items from Ministry of Finance.")
            all_news_data.extend(minfin_data)
        else:
            print("No news found from Ministry of Finance with current analysis. Check selectors in parse_minfin_news.")

    # AADE is still commented out due to 403 issues. Uncomment if AADE is fixed.
    # aade_html = fetch_page_content(cfg.AADE_NEWS_URL, headers=cfg.HEADERS, current_config=cfg)
    # if aade_html:
    #     aade_data = parse_aade_news(aade_html, current_config=cfg)
    #     if aade_data:
    #         print(f"Found {len(aade_data)} news items from AADE.")
    #         all_news_data.extend(aade_data)
    #     else:
    #         print("No news found from AADE with current analysis. Check selectors in parse_aade_news.")
    # else:
    #     print(f"Note: Failed to retrieve AADE page. 403 Forbidden is still possible.")

    capital_html = fetch_page_content(cfg.CAPITAL_NEWS_URL, headers=cfg.HEADERS, current_config=cfg)
    if capital_html:
        capital_data = parse_capital_news(capital_html, current_config=cfg)
        if capital_data:
            print(f"Found {len(capital_data)} news items from Capital.gr.")
            all_news_data.extend(capital_data)
        else:
            print("No news found from Capital.gr with current analysis. Check selectors in parse_capital_news.")

    if all_news_data:
        df = pd.DataFrame(all_news_data)
        df['id'] = df['url']

        greek_month_map = {
            'Ιανουαρίου': 'January', 'Φεβρουαρίου': 'February', 'Μαρτίου': 'March',
            'Απριλίου': 'April', 'Μαΐου': 'May', 'Ιουνίου': 'June',
            'Ιουλίου': 'July', 'Αυγούστου': 'August', 'Σεπτεμβρίου': 'September',
            'Οκτωβρίου': 'October', 'Νοεμβρίου': 'November', 'Δεκεμβρίου': 'December',
            'Ιαν': 'Jan', 'Φεβ': 'Feb', 'Μαρ': 'Mar', 'Απρ': 'Apr', 'Μαϊ': 'May',
            'Ιουν': 'Jun', 'Ιουλ': 'Jul', 'Αυγ': 'Aug', 'Σεπ': 'Sep', 'Οκτ': 'Oct',
            'Νοε': 'Nov', 'Δεκ': 'Dec'
        }

        date_formats = [
            '%d %B %Y',
            '%d/%m/%Y %H:%M',
            '%d/%m/%Y',
            '%d.%m.%Y',
            '%Y-%m-%d',
            '%d/%m',
            '%Y/%m/%d'
        ]

        df['date'] = df['date'].astype(str)

        def parse_date_robust(date_str):
            if pd.isna(date_str) or not date_str:
                return pd.NaT
            date_str_processed = str(date_str)
            for greek, english in greek_month_map.items():
                if greek in date_str_processed:
                    date_str_processed = date_str_processed.replace(greek, english)
            if re.search(r'^\d{2}/\d{2} \d{2}:\d{2}$', date_str_processed):
                if not re.search(r'\d{4}', date_str_processed):
                    current_year = pd.Timestamp.now().year
                    date_str_processed = f"{date_str_processed}/{current_year}"
            elif re.search(r'^\d{2}/\d{2}$', date_str_processed):
                if not re.search(r'\d{4}', date_str_processed):
                    current_year = pd.Timestamp.now().year
                    date_str_processed = f"{date_str_processed}/{current_year}"
            for fmt in date_formats:
                try:
                    return pd.to_datetime(date_str_processed, format=fmt, errors='raise')
                except (ValueError, TypeError):
                    continue
            return pd.NaT

        df['date'] = df['date'].apply(parse_date_robust)
        df = df.dropna(subset=['date'])

        if not df.empty:
            df['date'] = df['date'].dt.date
            if filter_by_current_date:
                df = df[df['date'] == today].copy()
                if df.empty:
                    print(f"No news found for the current date ({today}).")
                else:
                    print(f"Found {len(df)} news items for the current date ({today}).")

            df = df.sort_values(by='date', ascending=False).reset_index(drop=True)
            print(f"Total {len(df)} news/announcements found from sources (with valid date).")
            return df
        else:
            print("No valid date data found after parsing.")
            return pd.DataFrame()
    else:
        print("No news/announcements found from any source.")
        return pd.DataFrame()

if __name__ == "__main__":
    print("This script is meant to be imported and called from the main application.")
    print("Please run the Streamlit/Gradio app to execute the scraper functionality.")