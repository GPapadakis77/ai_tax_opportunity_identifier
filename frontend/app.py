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

def get_sentiment_emoji(sentiment):
    """Return emoji based on sentiment."""
    if sentiment == "ΘΕΤΙΚΟ":
        return "😊"
    elif sentiment == "ΑΡΝΗΤΙΚΟ":
        return "😠"
    else:
        return "😐"

# === INLINE CLASSES AND FUNCTIONS ===
# Since we can't import external modules, we define everything inline

class MockConfig:
    """Mock configuration class."""
    TAX_KEYWORDS = [
        "φόρος", "φορολογία", "ΦΠΑ", "ΕΝΦΙΑ", "εισόδημα", "κέρδη",
        "φορολογικά κίνητρα", "αφορολόγητο", "έκπτωση", "μείωση φόρων"
    ]
    
    OPPORTUNITY_KEYWORDS = [
        "κίνητρα", "επιδότηση", "ευκαιρία", "νέος νόμος", "αλλαγή",
        "προγράμματα", "χρηματοδότηση", "επενδύσεις"
    ]

class MockDBManager:
    """Mock database manager using SQLite."""
    
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

class MockLegislativeScraper:
    """Mock legislative scraper that returns sample data."""
    
    @staticmethod
    def get_latest_legislative_news(current_config=None, filter_by_current_date=True) -> pd.DataFrame:
        """Return mock legislative news data."""
        # Sample data for demonstration
        sample_data = {
            'title': [
                'Νέες φορολογικές ρυθμίσεις για επιχειρήσεις 2024',
                'Κίνητρα για πράσινες επενδύσεις στον τουρισμό',
                'Αλλαγές στο ΦΠΑ για ηλεκτρονικές υπηρεσίες',
                'Φορολογικά οφέλη για νεοφυείς επιχειρήσεις',
                'Νέο καθεστώς για ψηφιακούς νομάδες'
            ],
            'date': ['2024-08-01', '2024-08-02', '2024-08-03', '2024-08-04', '2024-08-05'],
            'source': ['Υπουργείο Οικονομικών'] * 5,
            'url': [
                'https://example.gov.gr/news1',
                'https://example.gov.gr/news2', 
                'https://example.gov.gr/news3',
                'https://example.gov.gr/news4',
                'https://example.gov.gr/news5'
            ],
            'content': [
                'Νέες ρυθμίσεις για τη φορολογία επιχειρήσεων με στόχο την ενίσχυση της ανταγωνιστικότητας...',
                'Κίνητρα για επενδύσεις σε πράσινες τεχνολογίες στον τομέα του τουρισμού...',
                'Σημαντικές αλλαγές στο καθεστώς ΦΠΑ για ψηφιακές υπηρεσίες...',
                'Ειδικό φορολογικό καθεστώς για startup και καινοτόμες επιχειρήσεις...',
                'Νέο πλαίσιο για την προσέλκυση ψηφιακών νομάδων στην Ελλάδα...'
            ]
        }
        
        return pd.DataFrame(sample_data)

class MockNLPProcessor:
    """Mock NLP processor."""
    
    def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process DataFrame with mock NLP analysis."""
        if df.empty:
            return df
        
        processed_df = df.copy()
        
        # Mock keyword extraction
        processed_df['keywords'] = processed_df['content'].apply(self._extract_keywords)
        
        # Mock topic identification
        processed_df['main_topic'] = processed_df['title'].apply(self._identify_topic)
        
        # Mock sentiment analysis
        processed_df['sentiment'] = processed_df['content'].apply(self._analyze_sentiment)
        
        return processed_df
    
    def _extract_keywords(self, text: str) -> str:
        """Mock keyword extraction."""
        keywords = []
        text_lower = text.lower()
        
        for keyword in MockConfig.TAX_KEYWORDS + MockConfig.OPPORTUNITY_KEYWORDS:
            if keyword.lower() in text_lower:
                keywords.append(keyword)
        
        return ', '.join(keywords[:5])  # Return top 5 keywords
    
    def _identify_topic(self, title: str) -> str:
        """Mock topic identification."""
        title_lower = title.lower()
        
        if 'φόρος' in title_lower or 'φορολογ' in title_lower:
            return 'Φορολογία'
        elif 'κίνητρα' in title_lower or 'επιδότηση' in title_lower:
            return 'Κίνητρα'
        elif 'επιχειρήσ' in title_lower:
            return 'Επιχειρήσεις'
        elif 'τουρισμ' in title_lower:
            return 'Τουρισμός'
        else:
            return 'Γενικά'
    
    def _analyze_sentiment(self, text: str) -> str:
        """Mock sentiment analysis."""
        positive_words = ['κίνητρα', 'οφέλη', 'ευκαιρί', 'βελτίωση', 'ενίσχυση']
        negative_words = ['μείωση', 'περικοπ', 'αύξηση φόρων', 'περιορισμ']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return 'ΘΕΤΙΚΟ'
        elif negative_count > positive_count:
            return 'ΑΡΝΗΤΙΚΟ'
        else:
            return 'ΟΥΔΕΤΕΡΟ'

class MockOpportunityIdentifier:
    """Mock opportunity identifier."""
    
    def identify_and_score_opportunities(self, df: pd.DataFrame) -> pd.DataFrame:
        """Identify and score opportunities."""
        if df.empty:
            return df
        
        opportunities_df = df.copy()
        
        # Calculate opportunity score
        opportunities_df['opportunity_score'] = opportunities_df.apply(self._calculate_score, axis=1)
        
        # Identify opportunity type
        opportunities_df['opportunity_type'] = opportunities_df.apply(self._identify_type, axis=1)
        
        # Filter only positive opportunities
        opportunities_df = opportunities_df[opportunities_df['opportunity_score'] > 0]
        
        return opportunities_df.sort_values('opportunity_score', ascending=False)
    
    def _calculate_score(self, row) -> float:
        """Calculate opportunity score (0-10)."""
        score = 5.0  # Base score
        
        # Boost score for positive sentiment
        if row.get('sentiment') == 'ΘΕΤΙΚΟ':
            score += 2.0
        elif row.get('sentiment') == 'ΑΡΝΗΤΙΚΟ':
            score -= 1.0
        
        # Boost score for opportunity keywords
        keywords = str(row.get('keywords', '')).lower()
        for keyword in MockConfig.OPPORTUNITY_KEYWORDS:
            if keyword.lower() in keywords:
                score += 1.0
        
        # Boost score for tax-related content
        content = str(row.get('content', '')).lower()
        if any(tax_word in content for tax_word in ['φόρος', 'φορολογ', 'κίνητρα']):
            score += 1.5
        
        return min(score, 10.0)  # Cap at 10
    
    def _identify_type(self, row) -> str:
        """Identify opportunity type."""
        title = str(row.get('title', '')).lower()
        content = str(row.get('content', '')).lower()
        
        if 'κίνητρα' in title or 'κίνητρα' in content:
            return 'Φορολογικά Κίνητρα'
        elif 'επιδότηση' in title or 'επιδότηση' in content:
            return 'Επιδοτήσεις'
        elif 'νέος νόμος' in title or 'νομοθεσία' in content:
            return 'Νομοθετικές Αλλαγές'
        elif 'επιχειρήσ' in title:
            return 'Επιχειρηματικές Ευκαιρίες'
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
    """Run the complete data pipeline."""
    with st.spinner("Εκτελείται η διαδικασία συλλογής & ανάλυσης δεδομένων... Αυτό μπορεί να διαρκέσει μερικά λεπτά."):
        # Initialize mock instances
        legislative_scraper = MockLegislativeScraper()
        nlp_processor = MockNLPProcessor()
        opportunity_identifier = MockOpportunityIdentifier()
        db_manager = MockDBManager()
        
        # Get latest news
        latest_legislative_news_df = legislative_scraper.get_latest_legislative_news(
            current_config=MockConfig, 
            filter_by_current_date=False
        )

        # Process with NLP
        processed_df = pd.DataFrame()
        if not latest_legislative_news_df.empty:
            processed_df = nlp_processor.process_dataframe(latest_legislative_news_df)
        
        # Identify opportunities
        identified_opportunities_df = pd.DataFrame()
        if not processed_df.empty:
            identified_opportunities_df = opportunity_identifier.identify_and_score_opportunities(processed_df)

        # Store in database
        if db_manager.connect():
            db_manager.create_table()
            if not identified_opportunities_df.empty:
                db_manager.insert_opportunities(identified_opportunities_df)
            db_manager.close()

    st.success("Η διαδικασία ολοκληρώθηκε! Τα δεδομένα ανανεώθηκαν.")
    return identified_opportunities_df

# === STREAMLIT APP ===

st.set_page_config(layout="wide", page_title="AI Product Opportunity Identifier")

st.header("AI Product Opportunity Identifier 💡")
st.markdown("Ανακαλύπτοντας νέες ευκαιρίες στους φορολογικούς και οικονομικούς τομείς.")

# Initialize instances
db_manager_instance = MockDBManager()

# --- Sidebar ---
with st.sidebar:
    st.title("Πίνακας Ελέγχου")

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

    if st.button("Ανανέωση Δεδομένων & Εντοπισμός Ευκαιριών", 
                 help="Εκτελέστε ξανά όλη τη διαδικασία για να βρείτε νέες ευκαιρίες."):
        st.session_state['refresh_data'] = True

    st.markdown("---")
    st.subheader("Σχετικά με την Εφαρμογή")
    st.info(
        "Αυτή η εφαρμογή συλλέγει αυτόματα φορολογικές και οικονομικές ειδήσεις, "
        "τις επεξεργάζεται με NLP, εντοπίζει πιθανές συμβουλευτικές ευκαιρίες και "
        "τις εμφανίζει σε έναν διαδραστικό πίνακα."
    )
    
    if st.button("Βοήθεια από το Chatbot 💬", 
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
                    identified_opportunities_df = all_stored_data_df[all_stored_data_df['opportunity_score'] > 0].copy()
                    identified_opportunities_df = identified_opportunities_df.sort_values(by='opportunity_score', ascending=False)
                else:
                    identified_opportunities_df = pd.DataFrame()
            else:
                identified_opportunities_df = pd.DataFrame()
            
            st.session_state['last_identified_df'] = identified_opportunities_df
    else:
        identified_opportunities_df = st.session_state['last_identified_df']

# --- Display Identified Opportunities ---
st.subheader("Επισκόπηση Εντοπισμένων Ευκαιριών")

if identified_opportunities_df.empty:
    st.warning("Δεν βρέθηκαν ευκαιρίες. Πατήστε 'Ανανέωση Δεδομένων' για να ξεκινήσετε.")
else:
    total_opportunities = len(identified_opportunities_df)
    st.info(f"Εμφανίζονται {total_opportunities} εντοπισμένες ευκαιρίες.")
    
    st.markdown("---")
    st.subheader("Φίλτρα & Αναζήτηση Αποτελεσμάτων")
    
    # Search and filters
    search_query = st.text_input("Αναζήτηση με Τίτλο ή Λέξεις-Κλειδιά:", "")
    
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        unique_sources = ["Όλες"] + list(identified_opportunities_df['source'].unique())
        selected_source = st.selectbox("Φίλτρο ανά Πηγή:", unique_sources)
    
    with col_filter2:
        unique_types = ["Όλοι"] + list(identified_opportunities_df['opportunity_type'].dropna().unique())
        selected_type = st.selectbox("Φίλτρο ανά Τύπο Ευκαιρίας:", unique_types)

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

    # Display results
    if filtered_df.empty:
        st.info("Δεν βρέθηκαν ευκαιρίες που να ταιριάζουν με τα επιλεγμένα φίλτρα.")
    else:
        display_cols = ['title', 'date', 'source', 'opportunity_score', 'opportunity_type', 'url', 'keywords', 'main_topic']
        
        st.dataframe(
            filtered_df[display_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "url": st.column_config.LinkColumn("URL", display_text="Σύνδεσμος"),
                "date": st.column_config.DateColumn("Ημερομηνία", format="DD/MM/YYYY"),
                "opportunity_score": st.column_config.NumberColumn(
                    "Βαθμολογία", 
                    help="Βαθμός Σημαντικότητας (υψηλότερος = καλύτερος)", 
                    format="%.1f"
                ),
                "opportunity_type": "Τύπος",
                "title": st.column_config.TextColumn("Τίτλος", width="large"),
            }
        )
        
        # Download button
        csv_data = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Λήψη Δεδομένων ως CSV",
            data=csv_data,
            file_name="identified_opportunities.csv",
            mime="text/csv"
        )

st.markdown("---")

# --- Chatbot Interface ---
if st.session_state.show_chatbot:
    st.subheader("Βοηθός Chatbot 💬")
    st.markdown("Ρωτήστε με για τις ευκαιρίες που εντοπίστηκαν ή για γενικά φορολογικά/οικονομικά θέματα!")
    
    # Initialize chat history
    if not st.session_state.chat_history:
        system_prompt = (
            "You are an expert AI assistant for Greek tax and economic topics. "
            "Your goal is to provide concise and helpful information. "
            "The user will provide you with context from a database along with their question. "
            "Base your answer primarily on this context. "
            "If the question is general and the answer is NOT in the context, "
            "then you are allowed to use your own general knowledge to provide an accurate answer."
        )
        st.session_state.chat_history.append({"role": "user", "parts": [{"text": system_prompt}]})
        st.session_state.chat_history.append({"role": "model", "parts": [{"text": "Καλησπέρα! Είμαι έτοιμος να απαντήσω στις ερωτήσεις σας."}]})

    # Display chat messages
    for message in st.session_state.chat_history[2:]:  # Skip system messages
        with st.chat_message(message["role"]):
            st.markdown(message["parts"][0]["text"])
    
    st.markdown("---")
    st.markdown("**Κάντε κλικ σε μια ερώτηση για να ξεκινήσετε:**")
    
    # Suggested questions
    suggested_questions = [
        "Ποιες είναι οι τελευταίες αλλαγές στη φορολογική νομοθεσία;",
        "Συνοψίστε τις σημαντικότερες ευκαιρίες.",
        "Πείτε μου για ευκαιρίες που σχετίζονται με κίνητρα."
    ]
    
    query_to_send = None
    cols = st.columns(len(suggested_questions))
    for i, question in enumerate(suggested_questions):
        if cols[i].button(question, key=f"suggested_q_{i}"):
            query_to_send = question
    
    # Chat input
    if user_input := st.chat_input("Η ερώτησή σας:"):
        query_to_send = user_input

    # Process user input
    if query_to_send:
        st.session_state.chat_history.append({"role": "user", "parts": [{"text": query_to_send}]})
        
        with st.chat_message("user"):
            st.markdown(query_to_send)

        with st.chat_message("assistant"):
            with st.spinner("Σκέφτομαι..."):
                # Prepare context from filtered data
                context_df = filtered_df if not filtered_df.empty else identified_opportunities_df
                context_str = ""
                
                if not context_df.empty:
                    for _, row in context_df.head(10).iterrows():
                        context_str += f"- Τίτλος: {row.get('title', 'N/A')}, Σκορ: {row.get('opportunity_score', 0):.1f}\n"
                
                # Generate response
                response_text = generate_gemini_response(
                    st.session_state.chat_history, 
                    gemini_api_key, 
                    context_str
                )
                st.markdown(response_text)
        
        st.session_state.chat_history.append({"role": "model", "parts": [{"text": response_text}]})
        st.rerun()