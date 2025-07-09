# data_ingestion/legislative_scraper.py

import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import sys
import re

# Προσθήκη του ριζικού φακέλου του project στο PATH για να βρίσκει το config
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config # Τώρα μπορούμε να εισάγουμε το config.py

def fetch_page_content(url, headers=None):
    """
    Ανακτά το περιεχόμενο HTML μιας ιστοσελίδας.
    """
    if headers is None:
        headers = config.HEADERS # Χρησιμοποιούμε τα headers από το config

    print(f"Προσπαθώ να ανακτήσω περιεχόμενο από: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=15) # Αυξάνουμε το timeout
        response.raise_for_status()  # Θα πετάξει εξαίρεση για HTTP λάθη (4xx ή 5xx)
        print(f"Επιτυχής ανάκτηση σελίδας {url}")
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Σφάλμα κατά την ανάκτηση της σελίδας {url}: {e}")
        return None

def parse_minfin_news(html_content):
    """
    Αναλύει τη σελίδα ειδήσεων του Υπουργείου Οικονομικών και εξάγει πληροφορίες.
    Προσαρμοσμένο με βάση τους selectors που παρείχθηκε για την αρχική σελίδα.
    """
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'lxml')
    news_entries = []

    articles = soup.find_all('article', class_=lambda x: x and 'elementor-post' in x.split() and 'elementor-grid-item' in x.split())

    if not articles:
        print("Σημείωση: Δεν βρέθηκαν 'article.elementor-post.elementor-grid-item' στη σελίδα του Υπουργείου Οικονομικών.")
        print("Ελέγξτε την HTML δομή της σελίδας 'https://www.minfin.gov.gr/news' με 'Inspect Element'.")
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
            date = date_tag.get_text(strip=True)

            news_entries.append({
                'title': title,
                'url': link,
                'date': date,
                'source': 'Υπουργείο Οικονομικών'
            })
    return news_entries

def parse_aade_news(html_content):
    """
    Αναλύει τη σελίδα δελτίων τύπου της ΑΑΔΕ και εξάγει πληροφορίες.
    Ενημερώθηκε με βάση το τελευταίο HTML snippet που παρείχθηκε για την ΑΑΔΕ.
    """
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'lxml')
    news_entries = []

    items = soup.find_all('div', class_='views-row')

    if not items:
        print("Σημείωση: Δεν βρέθηκαν 'div.views-row' στην σελίδα της ΑΑΔΕ.")
        print("Ελέγξτε την HTML δομή της 'https://www.aade.gr/deltia-typoy-anakoinoseis' με 'Inspect Element'.")
        return []

    for item in items:
        date_span = item.find('span', class_='field-content')
        link_tag = item.find('a', class_='category-item-title', href=True)
        title_text_element = item.find('p')

        if date_span and link_tag:
            date = date_span.get_text(strip=True)
            title = link_tag.get_text(strip=True) if link_tag else (title_text_element.get_text(strip=True) if title_text_element else "N/A Title")
            link = requests.compat.urljoin(config.AADE_NEWS_URL, link_tag['href'])

            news_entries.append({
                'title': title,
                'url': link,
                'date': date,
                'source': 'ΑΑΔΕ'
            })
    return news_entries

def parse_capital_news(html_content):
    """
    Αναλύει τη σελίδα ειδήσεων του Capital.gr και εξάγει πληροφορίες.
    ΕΝΗΜΕΡΩΜΕΝΟΙ SELECTORS βάσει του HTML snippet που παρείχατε.
    """
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'lxml')
    news_entries = []

    articles = soup.find_all('div', class_=lambda x: x and 'article' in x.split() and 'snip' in x.split())

    if not articles:
        print("Σημείωση: Δεν βρέθηκαν 'div.article.snip' στην σελίδα Capital.gr.")
        print("Ελέγξτε την HTML δομή της 'https://www.capital.gr/epikairotita' με 'Inspect Element'.")
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
            link = requests.compat.urljoin(config.CAPITAL_NEWS_URL, link_tag['href'])
            
            date_str = date_span.get_text(strip=True)
            time_str = time_span.get_text(strip=True) if time_span else "00:00"
            full_date_str = f"{date_str} {time_str}"

            news_entries.append({
                'title': title,
                'url': link,
                'date': full_date_str,
                'source': 'Capital.gr'
            })
    return news_entries


def get_latest_legislative_news():
    """
    Συλλέγει τα τελευταία νομοθετικά νέα και ανακοινώσεις από όλες τις πηγές.
    """
    all_news_data = []

    # 1. Από Υπουργείο Οικονομικών
    minfin_html = fetch_page_content(config.MINISTRY_FINANCE_NEWS_URL)
    if minfin_html:
        minfin_data = parse_minfin_news(minfin_html)
        if minfin_data:
            print(f"Βρέθηκαν {len(minfin_data)} νέα από Υπουργείο Οικονομικών.")
            all_news_data.extend(minfin_data)
        else:
            print("Δεν βρέθηκαν νέα από Υπουργείο Οικονομικών με την τρέχουσα ανάλυση. Ελέγξτε τους selectors στην parse_minfin_news.")

    # 2. Από ΑΑΔΕ (εξακολουθεί να είναι πιθανό το 403, αλλά το αφήνουμε)
    # Θα το αφήσουμε σχολιασμένο προς το παρόν για να εστιάσουμε στο Capital.gr
    # aade_html = fetch_page_content(config.AADE_NEWS_URL)
    # if aade_html:
    #     aade_data = parse_aade_news(aade_html)
    #     if aade_data:
    #         print(f"Βρέθηκαν {len(aade_data)} νέα από ΑΑΔΕ.")
    #         all_news_data.extend(aade_data)
    #     else:
    #         print("Δεν βρέθηκαν νέα από ΑΑΔΕ με την τρέχουσα ανάλυση. Ελέγξτε τους selectors στην parse_aade_news.")
    # else:
    #     print(f"Σημείωση: Αποτυχία ανάκτησης σελίδας ΑΑΔΕ. Εξακολουθεί να είναι πιθανό το 403 Forbidden.")


    # 3. Νέα πηγή: Capital.gr
    capital_html = fetch_page_content(config.CAPITAL_NEWS_URL)
    if capital_html:
        capital_data = parse_capital_news(capital_html)
        if capital_data:
            print(f"Βρέθηκαν {len(capital_data)} νέα από Capital.gr.")
            all_news_data.extend(capital_data)
        else:
            print("Δεν βρέθηκαν νέα από Capital.gr με την τρέχουσα ανάλυση. Ελέγξτε τους selectors στην parse_capital_news.")


    if all_news_data:
        df = pd.DataFrame(all_news_data)
        df['id'] = df['url'] # Απλό id προς το παρόν

        # Προσπάθεια μετατροπής ημερομηνιών σε standard format
        # Χρησιμοποιούμε μια πιο ολοκληρωμένη λίστα ελληνικών μηνών
        greek_month_map = {
            'Ιανουαρίου': 'January', 'Φεβρουαρίου': 'February', 'Μαρτίου': 'March',
            'Απριλίου': 'April', 'Μαΐου': 'May', 'Ιουνίου': 'June',
            'Ιουλίου': 'July', 'Αυγούστου': 'August', 'Σεπτεμβρίου': 'September',
            'Οκτωβρίου': 'October', 'Νοεμβρίου': 'November', 'Δεκεμβρίου': 'December',
            # Επίσης, για συντομογραφίες ή άλλες μορφές (π.χ. 'Ιουλ' από Capital.gr)
            'Ιαν': 'Jan', 'Φεβ': 'Feb', 'Μαρ': 'Mar', 'Απρ': 'Apr', 'Μαϊ': 'May',
            'Ιουν': 'Jun', 'Ιουλ': 'Jul', 'Αυγ': 'Aug', 'Σεπ': 'Sep', 'Οκτ': 'Oct',
            'Νοε': 'Nov', 'Δεκ': 'Dec'
        }

        # Date formats to try, ordered by likelihood/specificity
        date_formats = [
            '%d %B %Y',          # e.g., "9 July 2025" (after conversion from Greek)
            '%d/%m/%Y %H:%M',    # e.g., "09/07/2025 12:26" (for Capital.gr after appending year)
            '%d/%m/%Y',          # e.g., "09/07/2025" (for Capital.gr after appending year)
            '%d.%m.%Y',          # e.g., "09.07.2025"
            '%Y-%m-%d',          # e.g., "2025-07-09"
            '%d/%m',             # Fallback for DD/MM without year, handled by appending year in robust parse
            '%Y/%m/%d'
        ]

        df['date'] = df['date'].astype(str)

        def parse_date_robust(date_str):
            if pd.isna(date_str) or not date_str:
                return pd.NaT

            date_str_processed = str(date_str)

            # 1. Convert month names from Greek to English (full and abbreviated forms)
            for greek, english in greek_month_map.items():
                if greek in date_str_processed: # Use 'in' to handle cases like 'Ιουλίου'
                    date_str_processed = date_str_processed.replace(greek, english)

            # 2. Handle DD/MM and DD/MM HH:MM formats by appending current year if missing
            if re.search(r'^\d{2}/\d{2} \d{2}:\d{2}$', date_str_processed): # Exactly "DD/MM HH:MM"
                if not re.search(r'\d{4}', date_str_processed): # If year is missing
                    current_year = pd.Timestamp.now().year
                    date_str_processed = f"{date_str_processed}/{current_year}"
            elif re.search(r'^\d{2}/\d{2}$', date_str_processed): # Exactly "DD/MM"
                if not re.search(r'\d{4}', date_str_processed): # If year is missing
                    current_year = pd.Timestamp.now().year
                    date_str_processed = f"{date_str_processed}/{current_year}"
            
            # 3. Try parsing with all defined formats
            for fmt in date_formats:
                try:
                    # For `%B` format, ensure locale is set to 'en_US.utf8' if needed, or rely on month name replacement
                    # For simplicity and cross-platform consistency, relying on replacements is safer.
                    return pd.to_datetime(date_str_processed, format=fmt, errors='raise')
                except (ValueError, TypeError):
                    continue
            return pd.NaT # If no format matches

        df['date'] = df['date'].apply(parse_date_robust)

        # Remove rows that couldn't be converted to valid dates
        df = df.dropna(subset=['date'])

        if not df.empty:
            df['date'] = df['date'].dt.date # Keep only the date without time
            df = df.sort_values(by='date', ascending=False).reset_index(drop=True)
            print(f"Συνολικά βρέθηκαν {len(df)} νέα/ανακοινώσεις από τις πηγές (με έγκυρη ημερομηνία).")
            return df
        else:
            print("No valid date data found after parsing.")
            return pd.DataFrame()
    else:
        print("No news/announcements found from any source.")
        return pd.DataFrame()

if __name__ == "__main__":
    print("Εκτέλεση του legislative_scraper.py απευθείας (για δοκιμή).")
    latest_news_df = get_latest_legislative_news()
    if not latest_news_df.empty:
        print("\nΑποτελέσματα Νομοθετικών Νέων:")
        print(latest_news_df.head(10))

        output_dir = os.path.join(project_root, 'data')
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'latest_legislative_news.csv')
        latest_news_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\nΤα αποτελέσματα αποθηκεύτηκαν στο: {output_file}")
    else:
        print("Δεν βρέθηκαν αποτελέσματα για αποθήκευση.")