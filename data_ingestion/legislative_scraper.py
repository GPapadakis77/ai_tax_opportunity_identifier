import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import sys
import re
import importlib
from datetime import datetime

# Add the project root to the PATH to locate config module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config
importlib.reload(config)

def get_full_article_text(url, selectors, headers):
    """Fetches and parses the full text of a single article."""
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Try multiple body selectors
        body_selectors = selectors['body'].split(', ')
        article_body = None
        
        for body_selector in body_selectors:
            article_body = soup.select_one(body_selector.strip())
            if article_body:
                break
        
        if article_body:
            return article_body.get_text(separator='\n', strip=True)
        else:
            # Fallback: try to get any paragraph text
            paragraphs = soup.find_all('p')
            if paragraphs:
                return '\n'.join([p.get_text(strip=True) for p in paragraphs[:5]])
            return ""
            
    except Exception as e:
        print(f"    [DEBUG] Could not fetch full text from {url}: {e}")
        return ""

def parse_page_content(html_content, source_config):
    """
    Enhanced parser that uses multiple selectors from a config object to extract news.
    """
    if not html_content:
        return []
    
    soup = BeautifulSoup(html_content, 'lxml')
    news_entries = []
    
    # Try multiple container selectors
    container_selectors = source_config['selectors']['container'].split(', ')
    articles = []
    
    for container_selector in container_selectors:
        found_articles = soup.select(container_selector.strip())
        if found_articles:
            articles = found_articles
            print(f"  [DEBUG] For source '{source_config['name']}', using container selector '{container_selector.strip()}'. Found {len(articles)} article containers.")
            break
    
    if not articles:
        print(f"  [DEBUG] No articles found for source '{source_config['name']}' with any container selector.")
        return []

    # Get multiple selectors for each element
    title_selectors = source_config['selectors']['title'].split(', ')
    link_selectors = source_config['selectors']['link'].split(', ')
    date_selectors = source_config['selectors']['date'].split(', ')

    for i, article in enumerate(articles[:20]):  # Limit to first 20 articles
        title_tag = None
        link_tag = None  
        date_tag = None
        
        # Try multiple title selectors
        for title_selector in title_selectors:
            title_tag = article.select_one(title_selector.strip())
            if title_tag:
                break
        
        # Try multiple link selectors
        for link_selector in link_selectors:
            link_tag = article.select_one(link_selector.strip())
            if link_tag:
                break
        
        # Try multiple date selectors
        for date_selector in date_selectors:
            date_tag = article.select_one(date_selector.strip())
            if date_tag:
                break

        # Debug information
        print(f"    [DEBUG] Processing article #{i+1}: Title found: {bool(title_tag)}, Link found: {bool(link_tag)}, Date found: {bool(date_tag)}")

        # Extract information with fallbacks
        title = ""
        if title_tag:
            title = title_tag.get_text(strip=True)
        elif article.find('a'):  # Fallback: any link text
            title = article.find('a').get_text(strip=True)
        
        link = ""
        if link_tag and link_tag.get('href'):
            link = requests.compat.urljoin(source_config['url'], link_tag['href'])
        elif title_tag and title_tag.get('href'):
            link = requests.compat.urljoin(source_config['url'], title_tag['href'])
        
        date_str = ""
        if date_tag:
            date_str = date_tag.get_text(strip=True)
        else:
            # Fallback: look for any date-like text in the article
            date_pattern = r'\d{1,2}[:/\-\.]\d{1,2}[:/\-\.]\d{2,4}|\d{1,2}/\d{1,2}|\d{1,2}:\d{2}'
            date_match = re.search(date_pattern, article.get_text())
            if date_match:
                date_str = date_match.group()

        if title and link:  # Minimum required: title and link
            if not date_str:
                date_str = datetime.now().strftime('%d/%m/%Y')  # Use today's date as fallback
            
            news_entries.append({
                'title': title, 
                'url': link, 
                'date': date_str, 
                'source': source_config['name'],
                'content': title  # Use title as initial content
            })
            print(f"      [SUCCESS] Added article: {title[:50]}...")
        else:
            print(f"      [SKIP] Insufficient data for article #{i+1}")
            
    return news_entries

def parse_date_robust(date_str):
    """Enhanced date parsing with more flexibility."""
    if pd.isna(date_str) or not date_str:
        return pd.NaT
    
    date_str_processed = str(date_str).strip()
    
    # Handle Greek months
    for greek, english in config.GREEK_MONTH_MAP.items():
        date_str_processed = date_str_processed.replace(greek, english)
    
    # Clean up the date string
    date_str_processed = re.sub(r'[^\d\s:/\-\.\w]', '', date_str_processed)
    
    # Try standard formats
    for fmt in config.DATE_FORMATS:
        try:
            parsed_date = datetime.strptime(date_str_processed, fmt)
            if parsed_date.year == 1900:
                parsed_date = parsed_date.replace(year=datetime.now().year)
            return parsed_date
        except (ValueError, TypeError):
            continue
    
    # Try pandas parsing as last resort
    try:
        parsed_date = pd.to_datetime(date_str_processed, dayfirst=True)
        if parsed_date.year == 1900:
            parsed_date = parsed_date.replace(year=datetime.now().year)
        return parsed_date
    except (ValueError, TypeError):
        return pd.NaT

def get_latest_legislative_news(current_config=None, filter_by_current_date=False):
    """
    Enhanced news collection with better error handling and debugging.
    """
    all_news_data = []
    cfg = current_config if current_config else config
    
    for source_config in cfg.SOURCES:
        print(f"\n--- Scraping {source_config['name']} ---")
        try:
            response = requests.get(source_config['url'], headers=cfg.HEADERS, timeout=20)
            response.raise_for_status()
            html = response.text
            
            print(f"  [DEBUG] Successfully fetched page. HTML content length: {len(html)}")
            print(f"  [DEBUG] Response status: {response.status_code}")
            
            news_data = parse_page_content(html, source_config)
            if news_data:
                print(f"  [INFO] Found {len(news_data)} news items from {source_config['name']}.")
                all_news_data.extend(news_data)
            else:
                print(f"  [WARNING] No news items found from {source_config['name']}.")
                
        except requests.exceptions.RequestException as e:
            print(f"  [ERROR] Failed to retrieve page for {source_config['name']}: {e}")
        except Exception as e:
            print(f"  [ERROR] Unexpected error for {source_config['name']}: {e}")

    if not all_news_data:
        print("\nNo news found from any source.")
        return pd.DataFrame()

    df = pd.DataFrame(all_news_data)
    print(f"\n[INFO] Total {len(df)} raw news items collected.")
    
    # Enhanced date parsing
    print("[INFO] Parsing dates...")
    df['date'] = df['date'].apply(parse_date_robust)
    
    # Count successful date parsing
    valid_dates = df['date'].notna().sum()
    print(f"[INFO] Successfully parsed {valid_dates}/{len(df)} dates.")
    
    # Drop rows with invalid dates
    df = df.dropna(subset=['date'])
    df['date'] = df['date'].dt.date
    
    # Filter by current date if requested
    if filter_by_current_date:
        today = datetime.now().date()
        initial_count = len(df)
        df = df[df['date'] == today].copy()
        print(f"[INFO] Filtered to today's news: {len(df)}/{initial_count} articles.")
    
    # Fetch full text (can be slow, comment out for testing)
    if not df.empty:
        print("\n[INFO] Fetching full article texts...")
        def get_full_text_for_row(row):
            source_selectors = next(s['selectors'] for s in cfg.SOURCES if s['name'] == row['source'])
            return get_full_article_text(row['url'], source_selectors, cfg.HEADERS)
        
        df['full_text'] = df.apply(get_full_text_for_row, axis=1)
        
        # Count successful full text retrieval
        full_text_count = df[df['full_text'].str.len() > 0].shape[0]
        print(f"[INFO] Retrieved full text for {full_text_count}/{len(df)} articles.")
    
    # Sort by date (newest first)
    df = df.sort_values(by='date', ascending=False).reset_index(drop=True)
    
    print(f"\n[SUCCESS] Total {len(df)} news/announcements processed successfully.")
    
    # Show summary by source
    if not df.empty:
        print("\n[SUMMARY] Articles by source:")
        source_summary = df['source'].value_counts()
        for source, count in source_summary.items():
            print(f"  - {source}: {count} articles")
    
    return df

if __name__ == "__main__":
    print("Running enhanced scraper in standalone mode for testing...")
    test_df = get_latest_legislative_news()
    if not test_df.empty:
        print("\n--- Sample of Scraped Data ---")
        print(test_df[['title', 'source', 'date']].head())
        print(f"\n--- First article preview ---")
        if len(test_df) > 0:
            first_article = test_df.iloc[0]
            print(f"Title: {first_article['title']}")
            print(f"Source: {first_article['source']}")
            print(f"Date: {first_article['date']}")
            print(f"URL: {first_article['url']}")
            print(f"Content preview: {str(first_article.get('full_text', ''))[:200]}...")
    else:
        print("No articles found. Check the selectors and website structure.")