import streamlit as st
import pandas as pd
import os
import sys
import time
from datetime import datetime, date
import requests
import json
import re
from typing import Optional, Dict, List, Any
import sqlite3
import tempfile
import importlib.util

# Import the real scraper and config
try:
    # Add current directory and parent directory to Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    data_ingestion_dir = os.path.join(parent_dir, 'data_ingestion')
    
    # Add all relevant directories to path
    for directory in [current_dir, parent_dir, data_ingestion_dir]:
        if directory not in sys.path:
            sys.path.insert(0, directory)
    
    # Try to import from data_ingestion directory
    import config
    from legislative_scraper import get_latest_legislative_news
    
    # Use real config
    REAL_CONFIG = config
    SCRAPER_AVAILABLE = True
    st.success(f"✅ Modules φορτώθηκαν επιτυχώς από: {data_ingestion_dir}")
    
except ImportError as e:
    # Try alternative import method with specific paths
    try:
        # Get the correct paths
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        data_ingestion_dir = os.path.join(parent_dir, 'data_ingestion')
        
        # Import config.py from data_ingestion
        config_path = os.path.join(data_ingestion_dir, "config.py")
        scraper_path = os.path.join(data_ingestion_dir, "legislative_scraper.py")
        
        if os.path.exists(config_path) and os.path.exists(scraper_path):
            spec_config = importlib.util.spec_from_file_location("config", config_path)
            config = importlib.util.module_from_spec(spec_config)
            spec_config.loader.exec_module(config)
            
            spec_scraper = importlib.util.spec_from_file_location("legislative_scraper", scraper_path)
            legislative_scraper = importlib.util.module_from_spec(spec_scraper)
            spec_scraper.loader.exec_module(legislative_scraper)
            
            get_latest_legislative_news = legislative_scraper.get_latest_legislative_news
            REAL_CONFIG = config
            SCRAPER_AVAILABLE = True
            st.success(f"✅ Modules φορτώθηκαν με alternative method από: {data_ingestion_dir}")
        else:
            raise FileNotFoundError(f"Δεν βρέθηκαν τα αρχεία στο {data_ingestion_dir}")
        
    except Exception as e2:
        st.error(f"❌ Δεν βρέθηκαν τα modules config.py ή legislative_scraper.py")
        st.error(f"Πρώτη προσπάθεια: {e}")
        st.error(f"Δεύτερη προσπάθεια: {e2}")
        
        # Show debugging info
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        data_ingestion_dir = os.path.join(parent_dir, 'data_ingestion')
        
        st.info(f"Current directory: {current_dir}")
        st.info(f"Parent directory: {parent_dir}")
        st.info(f"Αναζητώ στο: {data_ingestion_dir}")
        
        # List files in directories
        if os.path.exists(data_ingestion_dir):
            files_in_data_ingestion = [f for f in os.listdir(data_ingestion_dir) if f.endswith('.py')]
            st.info(f"Python files στο data_ingestion: {files_in_data_ingestion}")
        else:
            st.error(f"Ο φάκελος data_ingestion δεν υπάρχει: {data_ingestion_dir}")
        
        files_in_current = [f for f in os.listdir(current_dir) if f.endswith('.py')]
        st.info(f"Python files στο current directory: {files_in_current}")
        
        SCRAPER_AVAILABLE = False
        
        # Fallback mock config
        class MockConfig:
            TAX_KEYWORDS = [
                "φόρος", "φορολογία", "ΦΠΑ", "ΕΝΦΙΑ", "εισόδημα", "κέρδη",
                "φορολογικά κίνητρα", "αφορολόγητο", "έκπτωση", "μείωση φόρων"
            ]
            
            OPPORTUNITY_KEYWORDS = [
                "κίνητρα", "επιδότηση", "ευκαιρία", "νέος νόμος", "αλλαγή",
                "προγράμματα", "χρηματοδότηση", "επενδύσεις"
            ]
        
        REAL_CONFIG = MockConfig


class DBManager:
    """Database manager using SQLite."""
    
    def __init__(self):
        # Create temporary database file
        self.db_path = os.path.join(tempfile.gettempdir(), "opportunities.db")
        self.connection = None
    
    def connect(self):
        """Connect to SQLite database."""
        try:
            self.connection = sqlite3.connect(self.db_path)
            return True
        except Exception as e:
            st.error(f"Database connection error: {e}")
            return False
    
    def create_table(self):
        """Create opportunities table if not exists."""
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    date TEXT,
                    source TEXT,
                    url TEXT,
                    content TEXT,
                    full_text TEXT,
                    keywords TEXT,
                    main_topic TEXT,
                    sentiment TEXT,
                    opportunity_score REAL,
                    opportunity_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.connection.commit()
            return True
        except Exception as e:
            st.error(f"Table creation error: {e}")
            return False
    
    def insert_opportunities(self, df: pd.DataFrame):
        """Insert opportunities into database."""
        if not self.connection or df.empty:
            return False
        
        try:
            df.to_sql('opportunities', self.connection, if_exists='append', index=False)
            self.connection.commit()
            return True
        except Exception as e:
            st.error(f"Insert error: {e}")
            return False
    
    def fetch_all_opportunities(self) -> pd.DataFrame:
        """Fetch all opportunities from database."""
        if not self.connection:
            return pd.DataFrame()
        
        try:
            query = "SELECT * FROM opportunities ORDER BY opportunity_score DESC"
            df = pd.read_sql_query(query, self.connection)
            return df
        except Exception as e:
            # If table doesn't exist, return empty DataFrame
            return pd.DataFrame()
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()


class NLPProcessor:
    """NLP processor for Greek text."""
    
    def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process DataFrame with NLP analysis."""
        if df.empty:
            return df
        
        processed_df = df.copy()
        
        # Extract keywords
        processed_df['keywords'] = processed_df.apply(
            lambda row: self._extract_keywords(row['title'] + ' ' + str(row.get('full_text', row.get('content', '')))), 
            axis=1
        )
        
        # Identify main topic
        processed_df['main_topic'] = processed_df['title'].apply(self._identify_topic)
        
        # Analyze sentiment
        processed_df['sentiment'] = processed_df.apply(
            lambda row: self._analyze_sentiment(row['title'] + ' ' + str(row.get('full_text', row.get('content', '')))), 
            axis=1
        )
        
        return processed_df
    
    def _extract_keywords(self, text: str) -> str:
        """Extract keywords from text."""
        keywords = []
        text_lower = text.lower()
        
        # Combine all keywords
        all_keywords = getattr(REAL_CONFIG, 'TAX_KEYWORDS', []) + getattr(REAL_CONFIG, 'OPPORTUNITY_KEYWORDS', [])
        
        for keyword in all_keywords:
            if keyword.lower() in text_lower:
                keywords.append(keyword)
        
        # Also check for partial matches
        tax_terms = ['φόρος', 'φορολογ', 'κίνητρα', 'επιδότηση', 'επένδυση', 'οικονομ']
        for term in tax_terms:
            if term in text_lower and term not in [k.lower() for k in keywords]:
                keywords.append(term)
        
        return ', '.join(keywords[:8])  # Return top 8 keywords
    
    def _identify_topic(self, title: str) -> str:
        """Identify main topic from title."""
        title_lower = title.lower()
        
        if any(word in title_lower for word in ['φόρος', 'φορολογ', 'φπα', 'ενφια']):
            return 'Φορολογία'
        elif any(word in title_lower for word in ['κίνητρα', 'επιδότηση', 'χρηματοδότηση']):
            return 'Κίνητρα & Επιδοτήσεις'
        elif any(word in title_lower for word in ['επιχειρήσ', 'εταιρ', 'startup']):
            return 'Επιχειρήσεις'
        elif any(word in title_lower for word in ['επένδυση', 'επενδυτ']):
            return 'Επενδύσεις'
        elif any(word in title_lower for word in ['τουρισμ', 'ξενοδοχ']):
            return 'Τουρισμός'
        elif any(word in title_lower for word in ['ακίνητ', 'real estate']):
            return 'Ακίνητα'
        elif any(word in title_lower for word in ['νόμος', 'νομοθεσ', 'κανονισμ']):
            return 'Νομοθεσία'
        else:
            return 'Γενικά'
    
    def _analyze_sentiment(self, text: str) -> str:
        """Analyze sentiment of text."""
        positive_words = [
            'κίνητρα', 'οφέλη', 'ευκαιρί', 'βελτίωση', 'ενίσχυση', 'μείωση φόρων', 
            'απλούστευση', 'επιδότηση', 'στήριξη', 'ανάπτυξη', 'προώθηση'
        ]
        negative_words = [
            'αύξηση φόρων', 'περικοπ', 'περιορισμ', 'πρόστιμο', 'κυρώσεις', 
            'μείωση επιδοτ', 'αυστηρότερ'
        ]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return 'ΘΕΤΙΚΟ'
        elif negative_count > positive_count:
            return 'ΑΡΝΗΤΙΚΟ'
        else:
            return 'ΟΥΔΕΤΕΡΟ'


class OpportunityIdentifier:
    """Opportunity identifier and scorer."""
    
    def identify_and_score_opportunities(self, df: pd.DataFrame) -> pd.DataFrame:
        """Identify and score opportunities."""
        if df.empty:
            return df
        
        opportunities_df = df.copy()
        
        # Calculate opportunity score
        opportunities_df['opportunity_score'] = opportunities_df.apply(self._calculate_score, axis=1)
        
        # Identify opportunity type
        opportunities_df['opportunity_type'] = opportunities_df.apply(self._identify_type, axis=1)
        
        # Filter only positive opportunities (score > 3.0)
        opportunities_df = opportunities_df[opportunities_df['opportunity_score'] > 3.0]
        
        return opportunities_df.sort_values('opportunity_score', ascending=False)
    
    def _calculate_score(self, row) -> float:
        """Calculate opportunity score (0-10)."""
        score = 4.0  # Base score
        
        title = str(row.get('title', '')).lower()
        content = str(row.get('full_text', row.get('content', ''))).lower()
        combined_text = title + ' ' + content
        
        # Boost score for positive sentiment
        if row.get('sentiment') == 'ΘΕΤΙΚΟ':
            score += 2.5
        elif row.get('sentiment') == 'ΑΡΝΗΤΙΚΟ':
            score -= 1.5
        
        # Boost score for opportunity keywords
        opportunity_words = ['κίνητρα', 'επιδότηση', 'χρηματοδότηση', 'στήριξη', 'ευκαιρί']
        for word in opportunity_words:
            if word in combined_text:
                score += 1.0
        
        # Boost score for tax-related content
        tax_words = ['φόρος', 'φορολογ', 'φπα', 'ενφια']
        for word in tax_words:
            if word in combined_text:
                score += 0.8
        
        # Boost for business-related content
        business_words = ['επιχειρήσ', 'εταιρ', 'startup', 'επένδυση']
        for word in business_words:
            if word in combined_text:
                score += 0.5
        
        # Boost for new laws/changes
        change_words = ['νέος νόμος', 'αλλαγ', 'τροποποίηση', 'νέο καθεστώς']
        for word in change_words:
            if word in combined_text:
                score += 1.2
        
        # Recency bonus (more recent = higher score)
        try:
            if 'date' in row:
                article_date = pd.to_datetime(row['date'])
                days_old = (datetime.now() - article_date).days
                if days_old <= 7:
                    score += 1.0
                elif days_old <= 30:
                    score += 0.5
        except:
            pass
        
        return min(score, 10.0)  # Cap at 10
    
    def _identify_type(self, row) -> str:
        """Identify opportunity type."""
        title = str(row.get('title', '')).lower()
        content = str(row.get('full_text', row.get('content', ''))).lower()
        combined_text = title + ' ' + content
        
        if any(word in combined_text for word in ['κίνητρα', 'φορολογικά κίνητρα']):
            return 'Φορολογικά Κίνητρα'
        elif any(word in combined_text for word in ['επιδότηση', 'χρηματοδότηση']):
            return 'Επιδοτήσεις & Χρηματοδότηση'
        elif any(word in combined_text for word in ['νέος νόμος', 'νομοθεσία', 'κανονισμ']):
            return 'Νομοθετικές Αλλαγές'
        elif any(word in combined_text for word in ['επιχειρήσ', 'startup', 'εταιρ']):
            return 'Επιχειρηματικές Ευκαιρίες'
        elif any(word in combined_text for word in ['επένδυση', 'επενδυτ']):
            return 'Επενδυτικές Ευκαιρίες'
        elif any(word in combined_text for word in ['φόρος', 'φορολογ', 'φπα']):
            return 'Φορολογικές Αλλαγές'
        else:
            return 'Γενικές Ευκαιρίες'


def generate_gemini_response(chat_history: List[Dict], api_key: str, context_str: str) -> str:
    """Generate response from Gemini API."""
    if not api_key:
        return "Παρακαλώ εισαγάγετε το Gemini API Key σας στην πλαϊνή μπάρα."

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    headers = {"Content-Type": "application/json"}
    
    # Prepare chat history
    api_chat_history = chat_history.copy()
    last_user_message = api_chat_history.pop() if api_chat_history else {"parts": [{"text": ""}]}
    
    # Create contextual prompt
    contextual_prompt = (
        f"Με βάση το παρακάτω πλαίσιο (context), απάντησε στην ερώτηση του χρήστη. "
        f"Αν η απάντηση δεν είναι στο πλαίσιο, χρησιμοποίησε τη γενική σου γνώση.\n"
        f"--- ΠΛΑΙΣΙΟ ---\n{context_str if context_str else 'Δεν υπάρχει διαθέσιμο πλαίσιο.'}\n"
        f"--- ΤΕΛΟΣ ΠΛΑΙΣΙΟΥ ---\n\n"
        f"Ερώτηση Χρήστη: {last_user_message['parts'][0]['text']}"
    )
    
    api_chat_history.append({"role": "user", "parts": [{"text": contextual_prompt}]})

    payload = {
        "contents": api_chat_history,
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1500}
    }

    # Retry mechanism
    for attempt in range(3):
        try:
            response = requests.post(api_url, headers=headers, data=json.dumps(payload), timeout=30)
            if response.status_code == 503:
                raise requests.exceptions.HTTPError("503 Server Error: Service Unavailable")
            response.raise_for_status()
            
            result = response.json()
            if result.get("candidates") and result["candidates"][0].get("content", {}).get("parts"):
                return result["candidates"][0]["content"]["parts"][0]["text"]
            else:
                return "Λήφθηκε μη αναμενόμενη απάντηση από το API."

        except requests.exceptions.RequestException as e:
            if attempt < 2:
                time.sleep(2)
            else:
                return f"Η κλήση API απέτυχε μετά από πολλαπλές προσπάθειες: {e}"
    
    return "Η υπηρεσία του API δεν είναι διαθέσιμη μετά από πολλαπλές προσπάθειες."


def run_pipeline() -> pd.DataFrame:
    """Run the complete data pipeline with real scraper."""
    with st.spinner("Εκτελείται η διαδικασία συλλογής & ανάλυσης δεδομένων... Αυτό μπορεί να διαρκέσει μερικά λεπτά."):
        
        # Initialize processors
        nlp_processor = NLPProcessor()
        opportunity_identifier = OpportunityIdentifier()
        db_manager = DBManager()
        
        try:
            if SCRAPER_AVAILABLE:
                st.info("Συλλογή δεδομένων από τις επίσημες πηγές...")
                # Use the real scraper
                latest_legislative_news_df = get_latest_legislative_news(
                    current_config=REAL_CONFIG, 
                    filter_by_current_date=False
                )
                
                if latest_legislative_news_df.empty:
                    st.warning("Δεν βρέθηκαν νέα άρθρα από τις πηγές.")
                    return pd.DataFrame()
                    
                st.success(f"Συλλέχθηκαν {len(latest_legislative_news_df)} άρθρα!")
            else:
                st.error("Ο scraper δεν είναι διαθέσιμος. Ελέγξτε τα αρχεία config.py και legislative_scraper.py.")
                return pd.DataFrame()

            # Process with NLP
            st.info("Επεξεργασία με NLP...")
            processed_df = nlp_processor.process_dataframe(latest_legislative_news_df)
            
            # Identify opportunities
            st.info("Εντοπισμός ευκαιριών...")
            identified_opportunities_df = opportunity_identifier.identify_and_score_opportunities(processed_df)

            # Store in database
            if db_manager.connect():
                db_manager.create_table()
                if not identified_opportunities_df.empty:
                    db_manager.insert_opportunities(identified_opportunities_df)
                    st.success(f"Αποθηκεύτηκαν {len(identified_opportunities_df)} ευκαιρίες στη βάση δεδομένων!")
                db_manager.close()

        except Exception as e:
            st.error(f"Σφάλμα κατά την εκτέλεση του pipeline: {e}")
            return pd.DataFrame()

    st.success("Η διαδικασία ολοκληρώθηκε! Τα δεδομένα ανανεώθηκαν.")
    return identified_opportunities_df


# === STREAMLIT APP ===

st.set_page_config(layout="wide", page_title="AI Product Opportunity Identifier")

st.header("AI Product Opportunity Identifier 💡")
st.markdown("Ανακαλύπτοντας νέες ευκαιρίες στους φορολογικούς και οικονομικούς τομείς.")

if not SCRAPER_AVAILABLE:
    st.error("⚠️ Τα απαραίτητα modules (config.py, legislative_scraper.py) δεν βρέθηκαν. Βεβαιωθείτε ότι βρίσκονται στον ίδιο φάκελο με το app.py.")

# Initialize database manager
db_manager_instance = DBManager()

# --- Sidebar ---
with st.sidebar:
    st.title("Πίνακας Ελέγχου")
    
    # Display scraper status
    if SCRAPER_AVAILABLE:
        st.success("✅ Scraper διαθέσιμος")
        if hasattr(REAL_CONFIG, 'SOURCES'):
            st.info(f"Πηγές: {len(REAL_CONFIG.SOURCES)}")
            for source in REAL_CONFIG.SOURCES:
                st.write(f"• {source['name']}")
    else:
        st.error("❌ Scraper μη διαθέσιμος")

    # Get Gemini API Key
    gemini_api_key = st.secrets.get("GEMINI_API_KEY") if hasattr(st, 'secrets') else None
    if not gemini_api_key:
        gemini_api_key = st.text_input(
            "Εισαγάγετε το Gemini API Key:", 
            type="password", 
            help="Μπορείτε να βρείτε το κλειδί σας στο Google AI Studio."
        )
        if not gemini_api_key:
            st.warning("Παρακαλώ εισαγάγετε το κλειδί API για να ενεργοποιήσετε το chatbot.")
        else:
            st.success("Το κλειδί API δόθηκε.")
    else:
        st.success("Το κλειδί API φορτώθηκε με επιτυχία.")

    if st.button("🔄 Ανανέωση Δεδομένων & Εντοπισμός Ευκαιριών", 
                 help="Εκτελέστε ξανά όλη τη διαδικασία για να βρείτε νέες ευκαιρίες.",
                 disabled=not SCRAPER_AVAILABLE):
        st.session_state['refresh_data'] = True

    st.markdown("---")
    st.subheader("Σχετικά με την Εφαρμογή")
    st.info(
        "Αυτή η εφαρμογή συλλέγει αυτόματα φορολογικές και οικονομικές ειδήσεις "
        "από επίσημες ελληνικές πηγές, τις επεξεργάζεται με NLP, εντοπίζει "
        "πιθανές συμβουλευτικές ευκαιρίες και τις εμφανίζει σε έναν διαδραστικό πίνακα."
    )
    
    if st.button("💬 Βοήθεια από το Chatbot", 
                 help="Ανοίξτε το chat για να κάνετε ερωτήσεις."):
        st.session_state['show_chatbot'] = not st.session_state.get('show_chatbot', False)
        st.rerun()
    
    st.markdown("---")

# --- Session State Initialization ---
if 'last_identified_df' not in st.session_state:
    st.session_state['last_identified_df'] = pd.DataFrame()
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []
if 'show_chatbot' not in st.session_state:
    st.session_state['show_chatbot'] = False
if 'refresh_data' not in st.session_state:
    st.session_state['refresh_data'] = False

# --- Data Loading Logic ---
if st.session_state.refresh_data:
    identified_opportunities_df = run_pipeline()
    st.session_state['last_identified_df'] = identified_opportunities_df
    st.session_state.chat_history = []
    st.session_state.refresh_data = False
    st.rerun()
else:
    if st.session_state.last_identified_df.empty:
        with st.spinner("Φόρτωση αρχικών δεδομένων από τη βάση..."):
            if db_manager_instance.connect():
                all_stored_data_df = db_manager_instance.fetch_all_opportunities()
                db_manager_instance.close()

                if not all_stored_data_df.empty:
                    identified_opportunities_df = all_stored_data_df[all_stored_data_df['opportunity_score'] > 3.0].copy()
                    identified_opportunities_df = identified_opportunities_df.sort_values(by='opportunity_score', ascending=False)
                else:
                    identified_opportunities_df = pd.DataFrame()
            else:
                identified_opportunities_df = pd.DataFrame()
            
            st.session_state['last_identified_df'] = identified_opportunities_df
    else:
        identified_opportunities_df = st.session_state['last_identified_df']

# --- Display Identified Opportunities ---
st.subheader("📊 Επισκόπηση Εντοπισμένων Ευκαιριών")

if identified_opportunities_df.empty:
    st.warning("Δεν βρέθηκαν ευκαιρίες. Πατήστε 'Ανανέωση Δεδομένων' για να ξεκινήσετε.")
    
    if SCRAPER_AVAILABLE:
        st.info("💡 Συμβουλή: Κάντε κλικ στο κουμπί 'Ανανέωση Δεδομένων' για να συλλέξετε τα τελευταία νέα από τις επίσημες πηγές.")
else:
    total_opportunities = len(identified_opportunities_df)
    avg_score = identified_opportunities_df['opportunity_score'].mean()
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Συνολικές Ευκαιρίες", total_opportunities)
    with col2:
        st.metric("Μέσος Βαθμός", f"{avg_score:.1f}")
    with col3:
        unique_sources = identified_opportunities_df['source'].nunique()
        st.metric("Πηγές", unique_sources)
    with col4:
        top_score = identified_opportunities_df['opportunity_score'].max()
        st.metric("Υψηλότερος Βαθμός", f"{top_score:.1f}")
    
    st.markdown("---")
    st.subheader("🔍 Φίλτρα & Αναζήτηση Αποτελεσμάτων")
    
    # Search and filters
    search_query = st.text_input("🔎 Αναζήτηση με Τίτλο ή Λέξεις-Κλειδιά:", "")
    
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    with col_filter1:
        unique_sources = ["Όλες"] + list(identified_opportunities_df['source'].unique())
        selected_source = st.selectbox("📰 Φίλτρο ανά Πηγή:", unique_sources)
    
    with col_filter2:
        unique_types = ["Όλοι"] + list(identified_opportunities_df['opportunity_type'].dropna().unique())
        selected_type = st.selectbox("🏷️ Φίλτρο ανά Τύπο Ευκαιρίας:", unique_types)
    
    with col_filter3:
        score_threshold = st.slider("⭐ Ελάχιστος Βαθμός:", 0.0, 10.0, 3.0, 0.5)

    # Apply filters
    filtered_df = identified_opportunities_df.copy()
    
    if search_query:
        filtered_df = filtered_df[
            filtered_df['title'].str.contains(search_query, case=False, na=False) |
            filtered_df['keywords'].str.contains(search_query, case=False, na=False)
        ]
    
    if selected_source != "Όλες":
        filtered_df = filtered_df[filtered_df['source'] == selected_source]
    
    if selected_type != "Όλοι":
        filtered_df = filtered_df[filtered_df['opportunity_type'] == selected_type]
    
    filtered_df = filtered_df[filtered_df['opportunity_score'] >= score_threshold]

    # Display results
    if filtered_df.empty:
        st.info("❌ Δεν βρέθηκαν ευκαιρίες που να ταιριάζουν με τα επιλεγμένα φίλτρα.")
    else:
        st.success(f"✅ Εμφανίζονται {len(filtered_df)} ευκαιρίες")
        
        # Display table
        display_cols = ['title', 'date', 'source', 'opportunity_score', 'opportunity_type', 'main_topic', 'sentiment', 'url', 'keywords']
        
        st.dataframe(
            filtered_df[display_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "title": st.column_config.TextColumn("📰 Τίτλος", width="large"),
                "date": st.column_config.DateColumn("📅 Ημερομηνία", format="DD/MM/YYYY"),
                "source": st.column_config.TextColumn("🔗 Πηγή", width="medium"),
                "opportunity_score": st.column_config.NumberColumn(
                    "⭐ Βαθμολογία", 
                    help="Βαθμός Σημαντικότητας (υψηλότερος = καλύτερος)", 
                    format="%.1f"
                ),
                "opportunity_type": st.column_config.TextColumn("🏷️ Τύπος", width="medium"),
                "main_topic": st.column_config.TextColumn("📋 Θέμα", width="medium"),
                "sentiment": st.column_config.TextColumn("😊 Sentiment", width="small"),
                "url": st.column_config.LinkColumn("🔗 Σύνδεσμος", display_text="Άρθρο"),
                "keywords": st.column_config.TextColumn("🔑 Λέξεις-Κλειδιά", width="large"),
            }
        )
        
        # Download button
        csv_data = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Λήψη Δεδομένων ως CSV",
            data=csv_data,
            file_name=f"identified_opportunities_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )

st.markdown("---")

# --- Chatbot Interface ---
if st.session_state.show_chatbot:
    st.subheader("🤖 Βοηθός Chatbot")
    st.markdown("Ρωτήστε με για τις ευκαιρίες που εντοπίστηκαν ή για γενικά φορολογικά/οικονομικά θέματα!")
    
    # Initialize chat history
    if not st.session_state.chat_history:
        system_prompt = (
            "You are an expert AI assistant for Greek tax and economic topics. "
            "Your goal is to provide concise and helpful information in Greek. "
            "The user will provide you with context from a database along with their question. "
            "Base your answer primarily on this context. "
            "If the question is general and the answer is NOT in the context, "
            "then you are allowed to use your own general knowledge to provide an accurate answer."
        )
        st.session_state.chat_history.append({"role": "user", "parts": [{"text": system_prompt}]})
        st.session_state.chat_history.append({"role": "model", "parts": [{"text": "Γεια σας! Είμαι έτοιμος να απαντήσω στις ερωτήσεις σας για φορολογικά και οικονομικά θέματα. Πώς μπορώ να σας βοηθήσω;"}]})

    # Display chat messages
    for message in st.session_state.chat_history[2:]:  # Skip system messages
        with st.chat_message(message["role"]):
            st.markdown(message["parts"][0]["text"])
    
    # Suggested questions
    if not identified_opportunities_df.empty:
        st.markdown("---")
        st.markdown("**💡 Προτεινόμενες ερωτήσεις:**")
        
        suggested_questions = [
            "Ποιες είναι οι σημαντικότερες ευκαιρίες με τον υψηλότερο βαθμό;",
            "Συνοψίστε τις φορολογικές αλλαγές που εντοπίστηκαν.",
            "Πείτε μου για ευκαιρίες που σχετίζονται με κίνητρα για επιχειρήσεις.",
            "Ποια άρθρα έχουν θετικό sentiment;",
            "Τι νέα υπάρχουν για το ΦΠΑ;"
        ]
        
        query_to_send = None
        cols = st.columns(3)
        for i, question in enumerate(suggested_questions):
            col_index = i % 3
            if cols[col_index].button(f"🔹 {question}", key=f"suggested_q_{i}"):
                query_to_send = question
    
    # Chat input
    if user_input := st.chat_input("💭 Γράψτε την ερώτησή σας εδώ..."):
        query_to_send = user_input

    # Process user input
    if 'query_to_send' in locals() and query_to_send:
        st.session_state.chat_history.append({"role": "user", "parts": [{"text": query_to_send}]})
        
        with st.chat_message("user"):
            st.markdown(query_to_send)

        with st.chat_message("assistant"):
            with st.spinner("Αναλύω τα δεδομένα..."):
                # Prepare context from filtered data
                context_df = filtered_df if not filtered_df.empty else identified_opportunities_df
                context_str = ""
                
                if not context_df.empty:
                    context_str = "ΔΙΑΘΕΣΙΜΕΣ ΕΥΚΑΙΡΙΕΣ:\n"
                    for i, (_, row) in enumerate(context_df.head(15).iterrows()):
                        context_str += f"\n{i+1}. Τίτλος: {row.get('title', 'N/A')}\n"
                        context_str += f"   Πηγή: {row.get('source', 'N/A')}\n"
                        context_str += f"   Ημερομηνία: {row.get('date', 'N/A')}\n"
                        context_str += f"   Βαθμολογία: {row.get('opportunity_score', 0):.1f}/10\n"
                        context_str += f"   Τύπος: {row.get('opportunity_type', 'N/A')}\n"
                        context_str += f"   Θέμα: {row.get('main_topic', 'N/A')}\n"
                        context_str += f"   Sentiment: {row.get('sentiment', 'N/A')}\n"
                        context_str += f"   Λέξεις-κλειδιά: {row.get('keywords', 'N/A')}\n"
                        if len(str(row.get('full_text', ''))) > 100:
                            context_str += f"   Περιεχόμενο: {str(row.get('full_text', ''))[:300]}...\n"
                        context_str += "   ---\n"
                
                # Generate response
                response_text = generate_gemini_response(
                    st.session_state.chat_history, 
                    gemini_api_key, 
                    context_str
                )
                st.markdown(response_text)
        
        st.session_state.chat_history.append({"role": "model", "parts": [{"text": response_text}]})
        st.rerun()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        <p>🏛️ Δεδομένα από επίσημες ελληνικές πηγές | 🤖 Powered by AI | 📊 Real-time Analysis</p>
    </div>
    """, 
    unsafe_allow_html=True
)