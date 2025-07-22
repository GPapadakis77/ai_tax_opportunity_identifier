import streamlit as st
import pandas as pd
import os
import sys
import importlib
from datetime import datetime, date
import requests
import json
import re

# --- Project Root Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Module Imports and Initialization ---
try:
    # These imports assume you have local files with these names.
    # If the app is a single file, you might not need these.
    import config
    importlib.reload(config)
    from data_ingestion import legislative_scraper
    importlib.reload(legislative_scraper)
    from nlp_processing import nlp_processor
    importlib.reload(nlp_processor)
    from database import db_manager
    importlib.reload(db_manager)
    from opportunity_identification import opportunity_identifier
    importlib.reload(opportunity_identifier)

    db_manager_instance = db_manager.DBManager()
    nlp_processor_instance = nlp_processor.NLPProcessor()
    opportunity_identifier_instance = opportunity_identifier.OpportunityIdentifier()

except Exception as e:
    # This error will show if the local files (config.py, etc.) are not found.
    st.error(f"Σφάλμα κατά τη φόρτωση των ενοτήτων: {e}")
    st.info("Βεβαιωθείτε ότι τα αρχεία .py (config, legislative_scraper, κ.λπ.) βρίσκονται στον σωστό κατάλογο.")
    st.stop()

st.set_page_config(layout="wide", page_title="AI Product Opportunity Identifier")

# --- Core Application Functions ---

def run_pipeline():
    """Scrapes, processes, and stores new opportunity data."""
    st.info("Εκτελείται η διαδικασία συλλογής & ανάλυσης δεδομένων... Αυτό μπορεί να διαρκέσει μερικά λεπτά.")
    
    latest_legislative_news_df = legislative_scraper.get_latest_legislative_news(current_config=config, filter_by_current_date=False)

    processed_df = pd.DataFrame()
    if not latest_legislative_news_df.empty:
        processed_df = nlp_processor_instance.process_dataframe(latest_legislative_news_df)
    
    identified_opportunities_df = pd.DataFrame()
    if not processed_df.empty:
        identified_opportunities_df = opportunity_identifier_instance.identify_and_score_opportunities(processed_df)

    db_manager_instance.connect()
    db_manager_instance.create_table()
    if not identified_opportunities_df.empty:
        db_manager_instance.insert_opportunities(identified_opportunities_df)
    db_manager_instance.close()

    st.success("Η διαδικασία ολοκληρώθηκε! Τα δεδομένα ανανεώθηκαν.")
    return identified_opportunities_df

def generate_gemini_response(chat_history, api_key):
    """Generates a response from the Gemini API based on chat history."""
    if not api_key:
        return "Παρακαλώ εισαγάγετε το Gemini API Key σας στην πλαϊνή μπάρα για να χρησιμοποιήσετε το chatbot."

    api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "contents": chat_history,
        "generationConfig": {
            "temperature": 0.6,
            "maxOutputTokens": 1024
        }
    }

    try:
        response = requests.post(f"{api_url}?key={api_key}", headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()

        if result.get("candidates") and result["candidates"][0].get("content", {}).get("parts"):
            return result["candidates"][0]["content"]["parts"][0]["text"]
        elif result.get("promptFeedback", {}).get("blockReason"):
            return f"Η απάντηση του μοντέλου μπλοκαρίστηκε λόγω: {result['promptFeedback']['blockReason']}. Παρακαλώ δοκιμάστε διαφορετική ερώτηση."
        else:
            st.error(f"Λήφθηκε μη αναμενόμενη δομή απάντησης από το API: {result}")
            return "Δεν ήταν δυνατή η λήψη έγκυρης απάντησης από το μοντέλο."
            
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            error_details = e.response.json()
            return f"Σφάλμα API (400 - Bad Request): Το αίτημα ήταν εσφαλμένο. Αυτό μπορεί να οφείλεται σε μη έγκυρο κλειδί API. Παρακαλώ ελέγξτε το κλειδί σας. Λεπτομέρειες: {error_details}"
        elif e.response.status_code == 403:
             return f"Σφάλμα API (403 - Forbidden): Το κλειδί API δεν έχει δικαιώματα για το Gemini API. Βεβαιωθείτε ότι το 'Generative Language API' είναι ενεργοποιημένο στο Google Cloud project σας."
        return f"Η κλήση API απέτυχε με σφάλμα HTTP: {e}. Ελέγξτε το κλειδί API και τη σύνδεσή σας στο διαδίκτυο."
    except Exception as e:
        return f"Προέκυψε ένα μη αναμενόμενο σφάλμα κατά την κλήση API: {e}"

# --- Main Streamlit UI ---

st.header("AI Product Opportunity Identifier 💡")
st.markdown("Ανακαλύπτοντας νέες ευκαιρίες στους φορολογικούς και οικονομικούς τομείς.")

# --- Sidebar ---
with st.sidebar:
    st.title("Πίνακας Ελέγχου")

    gemini_api_key = st.secrets.get("GEMINI_API_KEY")
    if not gemini_api_key:
        gemini_api_key = st.text_input("Εισαγάγετε το Gemini API Key:", type="password", help="Μπορείτε να βρείτε το κλειδί σας στο Google AI Studio.")
        if not gemini_api_key:
            st.warning("Παρακαλώ εισαγάγετε το κλειδί API για να ενεργοποιήσετε το chatbot.")
        else:
            st.success("Το κλειδί API δόθηκε.")
    else:
        st.success("Το κλειδί API φορτώθηκε με επιτυχία.")

    if st.button("Ανανέωση Δεδομένων & Εντοπισμός Ευκαιριών", help="Εκτελέστε ξανά όλη τη διαδικασία για να βρείτε νέες ευκαιρίες."):
        st.session_state['refresh_data'] = True

    st.markdown("---")
    st.subheader("Σχετικά με την Εφαρμογή")
    st.info(
        "Αυτή η εφαρμογή συλλέγει αυτόματα φορολογικές και οικονομικές ειδήσεις, τις επεξεργάζεται με NLP, "
        "εντοπίζει πιθανές συμβουλευτικές ευκαιρίες και τις εμφανίζει σε έναν διαδραστικό πίνακα."
    )
    if st.button("Βοήθεια από το Chatbot 💬", help="Ανοίξτε το chat για να κάνετε ερωτήσεις."):
        st.session_state['show_chatbot'] = not st.session_state.get('show_chatbot', False)
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
            db_manager_instance.connect()
            all_stored_data_df = db_manager_instance.fetch_all_opportunities()
            db_manager_instance.close()

            if not all_stored_data_df.empty:
                identified_opportunities_df = all_stored_data_df[all_stored_data_df['opportunity_score'] > 0].copy()
                identified_opportunities_df = identified_opportunities_df.sort_values(by='opportunity_score', ascending=False)
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
    
    search_query = st.text_input("Αναζήτηση με Τίτλο ή Λέξεις-Κλειδιά:", "")
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        unique_sources = ["Όλες"] + list(identified_opportunities_df['source'].unique())
        selected_source = st.selectbox("Φίλτρο ανά Πηγή:", unique_sources)
    with col_filter2:
        unique_types = ["Όλοι"] + list(identified_opportunities_df['opportunity_type'].dropna().unique())
        selected_type = st.selectbox("Φίλτρο ανά Τύπο Ευκαιρίας:", unique_types)

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
                "opportunity_score": st.column_config.NumberColumn("Βαθμολογία", help="Βαθμός Σημαντικότητας (υψηλότερος = καλύτερος)", format="%.1f"),
                "opportunity_type": "Τύπος",
                "title": st.column_config.TextColumn("Τίτλος", width="large"),
                "source": "Πηγή",
                "keywords": "Λέξεις-Κλειδιά",
                "main_topic": "Κύριο Θέμα"
            }
        )
        csv_data = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Λήψη Δεδομένων ως CSV",
            data=csv_data,
            file_name="identified_opportunities.csv",
            mime="text/csv"
        )

st.markdown("---")

# --- Chatbot Interface ---
if st.session_state.get('show_chatbot', False):
    st.subheader("Βοηθός Chatbot 💬")
    st.markdown("Ρωτήστε με για τις ευκαιρίες που εντοπίστηκαν ή για γενικά φορολογικά/οικονομικά θέματα!")

    initial_greeting = "Okay, I understand. I'm ready to assist with your questions about Greek tax and economic opportunities."
    
    if not st.session_state.chat_history:
        system_prompt = (
            "You are an AI assistant specialized in Greek tax and economic opportunities. "
            "Your goal is to provide concise and helpful information based on the provided context. "
            "If the question is about specific opportunities, refer to the provided context. "
            "If the context does not contain the answer, state that you cannot find it in the provided information. "
            "Format your answers clearly using markdown where appropriate."
        )
        st.session_state.chat_history.append({"role": "user", "parts": [{"text": system_prompt}]})
        st.session_state.chat_history.append({"role": "model", "parts": [{"text": initial_greeting}]})

    # Display chat history, but hide the initial system prompt and canned model response
    for message in st.session_state.chat_history:
        is_system_prompt = message["role"] == "user" and "specialized in Greek tax" in message["parts"][0]["text"]
        is_initial_greeting = message["role"] == "model" and message["parts"][0]["text"] == initial_greeting
        
        if not is_system_prompt and not is_initial_greeting:
            with st.chat_message(message["role"]):
                st.markdown(message["parts"][0]["text"])
    
    st.markdown("---")
    st.markdown("**Κάντε κλικ σε μια ερώτηση για να ξεκινήσετε:**")
    
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
    
    if user_input := st.chat_input("Η ερώτησή σας:"):
        query_to_send = user_input

    if query_to_send:
        st.session_state.chat_history.append({"role": "user", "parts": [{"text": query_to_send}]})
        
        with st.chat_message("user"):
            st.markdown(query_to_send)

        with st.chat_message("assistant"):
            with st.spinner("Σκέφτομαι..."):
                context_df = st.session_state.get('last_identified_df', pd.DataFrame())
                context_str = ""
                if not context_df.empty:
                    context_str = "Context from the database:\n"
                    for _, row in context_df.head(15).iterrows():
                        context_str += (
                            f"- Title: {row.get('title', 'N/A')}\n"
                            f"  Summary: {row.get('summary', 'N/A')}\n"
                            f"  Type: {row.get('opportunity_type', 'N/A')}\n"
                            f"  Score: {row.get('opportunity_score', 0):.1f}\n---\n"
                        )
                
                api_chat_history = st.session_state.chat_history.copy()
                api_chat_history.insert(-1, {"role": "user", "parts": [{"text": f"Use this context to answer the user's last question:\n{context_str}"}]})
                api_chat_history.insert(-1, {"role": "model", "parts": [{"text": "Okay, I will use the provided context."}]})

                response_text = generate_gemini_response(api_chat_history, gemini_api_key)
                st.markdown(response_text)
        
        st.session_state.chat_history.append({"role": "model", "parts": [{"text": response_text}]})
        st.rerun()