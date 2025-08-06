import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import sys
import re
import importlib
from datetime import datetime

# Add project root to PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config
importlib.reload(config)

def get_full_article_text(url, selectors, headers):
    """
    Fetches and parses the full body text of a single article using the specified body selector.
    """
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')
        article_body = soup.select_one(selectors['body'])
        if article_body:
            return article_body.get_text(separator='\n', strip=True)
        print(f"    [WARNING] Body selector '{selectors['body']}' not found for URL: {url}")
        return ""
    except Exception as e:
        print(f"    [ERROR] Could not fetch full text from {url}: {e}")
        return ""

def parse_page_content(html_content, source_config):
    """
    Uses source-specific selectors to extract article data from HTML content.
    Returns list of dicts with title, url, date, and source.
    """
    if not html_content:
        return []
    
    soup = BeautifulSoup(html_content, 'lxml')
    news_entries = []

    articles = soup.select(source_config['selectors']['container'])
    if not articles:
        print(f"No articles found for source '{source_config['name']}' using selector '{source_config['selectors']['container']}'.")
        return []

    for article in articles:
        title_tag = article.select_one(source_config['selectors']['title'])
        link_tag = article.select_one(source_config['selectors']['link'])
        date_tag = article.select_one(source_config['selectors']['date'])

        if title_tag and link_tag and date_tag:
            title = title_tag.get_text(strip=True)
            link = requests.compat.urljoin(source_config['url'], link_tag['href'])
            date_str = date_tag.get_text(strip=True)

            news_entries.append({
                'title': title,
                'url': link,
                'date': date_str,
                'source': source_config['name']
            })

    return news_entries

def parse_date_robust(date_str):
    """
    Attempts to parse a date string in various known formats, including Greek formats.
    """
    if pd.isna(date_str) or not date_str:
        return pd.NaT

    date_str_processed = str(date_str)
    
    # Replace Greek months with English
    for greek, english in config.GREEK_MONTH_MAP.items():
        date_str_processed = date_str_processed.replace(greek, english)

    for fmt in config.DATE_FORMATS:
        try:
            parsed_date = datetime.strptime(date_str_processed, fmt)
            if parsed_date.year == 1900:  # e.g. %d/%m
                parsed_date = parsed_date.replace(year=datetime.now().year)
            return parsed_date
        except (ValueError, TypeError):
            continue

    # Fallback using pandas
    try:
        return pd.to_datetime(date_str_processed, errors='coerce')
    except Exception:
        return pd.NaT

def get_latest_legislative_news(current_config=None, filter_by_current_date=False):
    """
    Iterates through configured news sources and scrapes headlines, links, dates and full text.
    Optionally filters for today's news only.
    """
    all_news_data = []
    cfg = current_config if current_config else config

    for source_config in cfg.SOURCES:
        print(f"\n--- Scraping: {source_config['name']} ---")
        try:
            response = requests.get(source_config['url'], headers=cfg.HEADERS, timeout=20)
            response.raise_for_status()
            html = response.text
            news_data = parse_page_content(html, source_config)
            if news_data:
                print(f"  ✓ Found {len(news_data)} items.")
                all_news_data.extend(news_data)
            else:
                print("  ⚠ No news extracted from this source.")
        except requests.RequestException as e:
            print(f"  [ERROR] Failed to retrieve page: {e}")

    if not all_news_data:
        print("No news found from any source.")
        return pd.DataFrame()

    df = pd.DataFrame(all_news_data)

    # Convert to datetime
    df['date'] = df['date'].apply(parse_date_robust)
    df = df.dropna(subset=['date'])
    df['date'] = df['date'].dt.date

    # Optional: Filter for today's news only
    if filter_by_current_date:
        today = datetime.now().date()
        df = df[df['date'] == today].copy()
        print(f"  📅 Filtered to today's news only: {len(df)} items.")

    # Fetch full text per article
    print("Fetching full article texts...")
    try:
        df['full_text'] = df.apply(
            lambda row: get_full_article_text(
                row['url'],
                next(s['selectors'] for s in cfg.SOURCES if s['name'] == row['source']),
                cfg.HEADERS
            ),
            axis=1
        )
    except Exception as e:
        print(f"[ERROR] Exception during full text fetching: {e}")
        df['full_text'] = ""

    df = df.sort_values(by='date', ascending=False).reset_index(drop=True)
    print(f"\n✅ Total {len(df)} news articles processed successfully.")
    return df

# CLI entry point
if __name__ == "__main__":
    print("Running scraper in standalone mode for testing...\n")
    df = get_latest_legislative_news()
    if not df.empty:
        print("\n--- Sample of Scraped News ---")
        print(df[['date', 'title', 'source']].head())
    else:
        print("⚠ No data scraped.")
