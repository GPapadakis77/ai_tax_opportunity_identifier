# frontend/app.py

import streamlit as st
import pandas as pd
import os
import sys
import importlib # Για να κάνουμε reload τα modules

# Προσθήκη του ριζικού φακέλου του project στο PATH για να βρίσκει τα modules
# Αυτό είναι κρίσιμο για να βρει τα data_ingestion, nlp_processing, κλπ.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Αναγκαστική επαναφόρτωση των modules για να βλέπουν τις τελευταίες αλλαγές
# Αυτό είναι σημαντικό όταν τρέχουμε Streamlit μετά από αλλαγές στον κώδικα.
try:
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

    # Εκκίνηση των κλάσεων
    db_manager_instance = db_manager.DBManager()
    nlp_processor_instance = nlp_processor.NLPProcessor()
    opportunity_identifier_instance = opportunity_identifier.OpportunityIdentifier()

except Exception as e:
    st.error(f"Σφάλμα κατά τη φόρτωση των modules ή την εκκίνηση των κλάσεων: {e}")
    st.stop() # Σταματάμε την εφαρμογή Streamlit αν υπάρχει πρόβλημα

st.set_page_config(layout="wide", page_title="AI Product Opportunity Identifier")

# --- Streamlit UI ---
st.title("AI Product Opportunity Identifier")
st.markdown("Εντοπισμός νέων ευκαιριών για φορολογικές συμβουλευτικές υπηρεσίες.")

# Sidebar για επιλογές
st.sidebar.header("Επιλογές")
refresh_button = st.sidebar.button("Ανανέωση Δεδομένων & Εντοπισμός Ευκαιριών")

# Λειτουργία ανανέωσης δεδομένων
@st.cache_data(ttl=3600) # Cache τα δεδομένα για 1 ώρα
def run_pipeline():
    """
    Εκτελεί ολόκληρη τη pipeline: scraping, NLP, αναγνώριση ευκαιριών, αποθήκευση.
    """
    st.info("Εκτελώ τη διαδικασία συλλογής & ανάλυσης δεδομένων... Παρακαλώ περιμένετε.")
    
    # 1. Εκτέλεση Scraper
    latest_legislative_news_df = legislative_scraper.get_latest_legislative_news(config)

    # 2. Επεξεργασία NLP
    processed_df = pd.DataFrame()
    if not latest_legislative_news_df.empty:
        processed_df = nlp_processor_instance.process_dataframe(latest_legislative_news_df)
    
    # 3. Αναγνώριση & Βαθμολόγηση Ευκαιριών
    identified_opportunities_df = pd.DataFrame()
    if not processed_df.empty:
        identified_opportunities_df = opportunity_identifier_instance.identify_and_score_opportunities(processed_df)

    # 4. Αποθήκευση στη βάση δεδομένων
    db_manager_instance.connect()
    db_manager_instance.create_table() # Διασφαλίζει ότι ο πίνακας είναι ενημερωμένος
    if not processed_df.empty:
        # Βεβαιωθείτε ότι το processed_df έχει τις στήλες opportunity_score και opportunity_type
        for col in ['opportunity_score', 'opportunity_type']:
            if col not in processed_df.columns:
                processed_df[col] = None
        db_manager_instance.insert_opportunities(processed_df)
    db_manager_instance.close()

    st.success("Η διαδικασία ολοκληρώθηκε!")
    return identified_opportunities_df

# Εκτέλεση της pipeline όταν πατηθεί το κουμπί ή για πρώτη φόρα
if refresh_button:
    identified_opportunities_df = run_pipeline()
else:
    # Ανάκτηση των πιο πρόσφατων δεδομένων από τη βάση κατά την αρχική φόρτωση
    st.info("Φορτώνω τα τελευταία δεδομένα από τη βάση δεδομένων...")
    db_manager_instance.connect()
    all_stored_data_df = db_manager_instance.fetch_all_opportunities()
    db_manager_instance.close()

    if not all_stored_data_df.empty:
        identified_opportunities_df = all_stored_data_df[all_stored_data_df['opportunity_score'] > 0].copy()
        identified_opportunities_df = identified_opportunities_df.sort_values(by='opportunity_score', ascending=False)
    else:
        identified_opportunities_df = pd.DataFrame() # Κενό DataFrame αν δεν υπάρχουν δεδομένα

# Εμφάνιση των αποτελεσμάτων
st.header("Εντοπισμένες Ευκαιρίες")

if identified_opportunities_df.empty:
    st.warning("Δεν βρέθηκαν ευκαιρίες αυτή τη στιγμή. Πατήστε 'Ανανέωση Δεδομένων' για να συλλέξετε νέα.")
else:
    # Φιλτράρισμα και εμφάνιση
    col1, col2 = st.columns(2)
    with col1:
        selected_source = st.selectbox("Φιλτράρισμα ανά Πηγή:", ["Όλες"] + list(identified_opportunities_df['source'].unique()))
    with col2:
        selected_type = st.selectbox("Φιλτράρισμα ανά Τύπο Ευκαιρίας:", ["Όλοι"] + list(identified_opportunities_df['opportunity_type'].unique()))

    filtered_df = identified_opportunities_df.copy()
    if selected_source != "Όλες":
        filtered_df = filtered_df[filtered_df['source'] == selected_source]
    if selected_type != "Όλοι":
        filtered_df = filtered_df[filtered_df['opportunity_type'] == selected_type]

    if filtered_df.empty:
        st.info("Δεν βρέθηκαν ευκαιρίες με τα επιλεγμένα φίλτρα.")
    else:
        st.dataframe(
            filtered_df[[
                'title', 'date', 'source', 'opportunity_score', 'opportunity_type', 'url', 'keywords', 'main_topic'
            ]].style.format({'opportunity_score': "{:.1f}"}), # Μορφοποίηση score
            use_container_width=True,
            hide_row_index=True,
            column_config={
                "url": st.column_config.LinkColumn("URL", display_text="Άρθρο"),
                "date": st.column_config.DateColumn("Ημερομηνία", format="DD/MM/YYYY"),
                "opportunity_score": st.column_config.NumberColumn("Σκορ", help="Βαθμολογία Σημασίας"),
                "opportunity_type": st.column_config.TextColumn("Τύπος Ευκαιρίας"),
                "title": st.column_config.TextColumn("Τίτλος", width="large"),
                "source": st.column_config.TextColumn("Πηγή"),
                "keywords": st.column_config.TextColumn("Λέξεις-Κλειδιά"),
                "main_topic": st.column_config.TextColumn("Κύριο Θέμα")
            }
        )

st.markdown("---")
st.markdown("Για περισσότερες πληροφορίες ή τεχνική υποστήριξη, επικοινωνήστε με την ομάδα ανάπτυξης.")