# config.py

SOURCES = [
    {
        'name': 'Ministry of Finance',
        'url': 'https://www.minfin.gr/news',
        'selectors': { 'container': 'article.elementor-post', 'title': 'h3.elementor-post__title a', 'link': 'h3.elementor-post__title a', 'date': 'span.elementor-post-date', 'body': 'div.elementor-widget-theme-post-content'}
    },
    {
        'name': 'Capital.gr',
        'url': 'https://www.capital.gr/epikairotita',
        'selectors': { 'container': 'div.article.snip', 'title': 'h2.bold a', 'link': 'h2.bold a', 'date': 'span.date', 'body': 'div.text'}
    }
]

# --- NLP & Scoring Keywords (EXPANDED) ---
TAX_KEYWORDS = [
    # Core Tax/Finance Keywords
    "φορολογία", "φορολογικές αλλαγές", "φορολογικός νόμος", "φορολογικές διατάξεις",
    "ΦΠΑ", "εισόδημα", "ΑΑΔΕ", "φορολογικός έλεγχος",
    "παράταση", "τροποποίηση", "νέο νομοσχέδιο", "κίνητρα", "επιδοτήσεις",
    "φορολογικές δηλώσεις", "ηλεκτρονικά βιβλία", "mydata", "λογιστικά",

    # General Business & Economy Keywords
    "επένδυση", "επενδύσεις", "εξαγορά", "συγχώνευση", "startup",
    "ανάπτυξη", "επιχειρηματικότητα", "χρηματιστήριο", "ομόλογα",
    "οικονομία", "real estate", "υποδομές", "διαγωνισμός", "ακίνητα", "κεφάλαιο"
]

DATABASE_NAME = "tax_opportunities.db"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
HEADERS = {'User-Agent': USER_AGENT}

GREEK_MONTH_MAP = {
    'Ιανουαρίου': 'January', 'Φεβρουαρίου': 'February', 'Μαρτίου': 'March', 'Απριλίου': 'April', 'Μαΐου': 'May', 'Ιουνίου': 'June', 'Ιουλίου': 'July', 'Αυγούστου': 'August', 'Σεπτεμβρίου': 'September', 'Οκτωβρίου': 'October', 'Νοεμβρίου': 'November', 'Δεκεμβρίου': 'December',
    'Ιαν': 'Jan', 'Φεβ': 'Feb', 'Μαρ': 'Mar', 'Απρ': 'Apr', 'Μαϊ': 'May', 'Ιουν': 'Jun', 'Ιουλ': 'Jul', 'Αυγ': 'Aug', 'Σεπ': 'Sep', 'Οκτ': 'Oct', 'Νοε': 'Nov', 'Δεκ': 'Dec'
}

DATE_FORMATS = [
    '%d %B %Y', '%d/%m/%Y %H:%M', '%d/%m/%Y', '%d.%m.%Y', '%Y-%m-%d'
]