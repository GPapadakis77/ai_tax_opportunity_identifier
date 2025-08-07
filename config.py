# config.py - Updated with correct selectors

SOURCES = [
    {
        'name': 'Ministry of Finance',
        'url': 'https://www.minfin.gr/news',
        'selectors': {
            'container': 'article.elementor-post',
            'title': 'h3.elementor-post__title a',
            'link': 'h3.elementor-post__title a',
            'date': 'span.elementor-post-date',
            'body': 'div.elementor-widget-theme-post-content'
        }
    },
    {
        'name': 'Capital.gr',
        'url': 'https://www.capital.gr/epikairotita/',
        'selectors': {
            'container': 'article.teaser, .article-item, .news-item',  # Multiple possible containers
            'title': 'h2 a, h3 a, .title a, .headline a',  # Multiple title selectors
            'link': 'h2 a, h3 a, .title a, .headline a',   # Same as title for links
            'date': '.date, .publish-date, .time, span.date',  # Multiple date selectors
            'body': '.content, .excerpt, .summary, p'  # Multiple body selectors
        }
    },
    {
        'name': 'Capital.gr Alternative',
        'url': 'https://www.capital.gr/oikonomia/',  # Try economy section
        'selectors': {
            'container': 'article, .article, .news-article',
            'title': 'h2 a, h3 a, .title',
            'link': 'h2 a, h3 a, .title a',
            'date': '.date, .publish-date, time',
            'body': '.content, .text, p'
        }
    }
]

# Enhanced keywords for better opportunity detection
TAX_KEYWORDS = [
    # Core Tax/Finance Keywords
    "φορολογία", "φορολογικές αλλαγές", "φορολογικός νόμος", "φορολογικές διατάξεις",
    "ΦΠΑ", "εισόδημα", "ΑΑΔΕ", "φορολογικός έλεγχος", "φόρος", "φόροι",
    "παράταση", "τροποποίηση", "νέο νομοσχέδιο", "κίνητρα", "επιδοτήσεις",
    "φορολογικές δηλώσεις", "ηλεκτρονικά βιβλία", "mydata", "λογιστικά",
    "ΕΝΦΙΑ", "τέλη κυκλοφορίας", "αφορολόγητο", "έκπτωση φόρου",
    
    # Business & Economy Keywords
    "επένδυση", "επενδύσεις", "εξαγορά", "συγχώνευση", "startup",
    "ανάπτυξη", "επιχειρηματικότητα", "χρηματιστήριο", "ομόλογα",
    "οικονομία", "real estate", "υποδομές", "διαγωνισμός", "ακίνητα", "κεφάλαιο",
    "χρηματοδότηση", "δάνεια", "τράπεζες", "πιστώσεις", "επιχειρήσεις",
    
    # Government & Policy
    "υπουργείο", "κυβέρνηση", "νομοσχέδιο", "διάταγμα", "κανονισμός",
    "πρόγραμμα", "σχέδιο", "μέτρα", "πολιτική", "στρατηγική"
]

OPPORTUNITY_KEYWORDS = [
    "κίνητρα", "επιδότηση", "επιδοτήσεις", "ευκαιρία", "ευκαιρίες",
    "νέος νόμος", "αλλαγή", "αλλαγές", "βελτίωση", "ενίσχυση",
    "προγράμματα", "χρηματοδότηση", "επενδύσεις", "στήριξη",
    "απλούστευση", "διευκόλυνση", "μείωση φόρων", "φοροαπαλλαγή",
    "νέο καθεστώς", "ειδικό καθεστώς", "προνομιακό καθεστώς",
    "digital nomad", "ψηφιακός νομάδας", "startup", "καινοτομία",
    "πράσινη ανάπτυξη", "βιώσιμη ανάπτυξη", "ψηφιακή μετάβαση"
]

DATABASE_NAME = "tax_opportunities.db"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
HEADERS = {'User-Agent': USER_AGENT}

GREEK_MONTH_MAP = {
    'Ιανουαρίου': 'January', 'Φεβρουαρίου': 'February', 'Μαρτίου': 'March',
    'Απριλίου': 'April', 'Μαΐου': 'May', 'Ιουνίου': 'June',
    'Ιουλίου': 'July', 'Αυγούστου': 'August', 'Σεπτεμβρίου': 'September',
    'Οκτωβρίου': 'October', 'Νοεμβρίου': 'November', 'Δεκεμβρίου': 'December',
    'Ιαν': 'Jan', 'Φεβ': 'Feb', 'Μαρ': 'Mar', 'Απρ': 'Apr',
    'Μαϊ': 'May', 'Ιουν': 'Jun', 'Ιουλ': 'Jul', 'Αυγ': 'Aug',
    'Σεπ': 'Sep', 'Οκτ': 'Oct', 'Νοε': 'Nov', 'Δεκ': 'Dec'
}

DATE_FORMATS = [
    '%d %B %Y', '%d/%m/%Y %H:%M', '%d/%m/%Y', '%d.%m.%Y', '%Y-%m-%d',
    '%H:%M %d/%m', '%d/%m %H:%M'  # Added more flexible formats
]