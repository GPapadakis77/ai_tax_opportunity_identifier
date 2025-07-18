import streamlit as st
import pandas as pd
import os
import sys
import importlib
from datetime import datetime, date

# Add the project root to the PATH to locate modules
# This is crucial for finding data_ingestion, nlp_processing, etc.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Force reload modules to ensure the latest changes are picked up
# This is important when running Streamlit after code changes.
try:
    import config
    importlib.reload(config)
    # IMPORT THE SCRAPER MODULE
    from data_ingestion import legislative_scraper
    importlib.reload(legislative_scraper)
    from nlp_processing import nlp_processor
    importlib.reload(nlp_processor)
    from database import db_manager
    importlib.reload(db_manager)
    from opportunity_identification import opportunity_identifier
    importlib.reload(opportunity_identifier)

    # Initialize classes
    db_manager_instance = db_manager.DBManager()
    nlp_processor_instance = nlp_processor.NLPProcessor()
    opportunity_identifier_instance = opportunity_identifier.OpportunityIdentifier()

except Exception as e:
    st.error(f"Error loading modules or initializing classes: {e}")
    st.stop() # Stop the Streamlit app if there's a problem

# Set Streamlit page configuration
st.set_page_config(layout="wide", page_title="AI Product Opportunity Identifier")

# --- Custom CSS for Grant Thornton Theme (Purple, Grey, White) ---
st.markdown("""
<style>
    /* General Variables for easier theme management */
    :root {
        --gt-purple-dark: #4D148C; /* Grant Thornton Primary Purple */
        --gt-purple-light: #5C2D91; /* Slightly lighter purple for containers */
        --gt-grey-dark: #333333;   /* Dark Grey for sidebar, input backgrounds */
        --gt-grey-medium: #666666; /* Medium Grey for table headers, borders */
        --gt-grey-light: #CCCCCC;  /* Light Grey for button backgrounds, borders */
        --text-white: #FFFFFF;     /* White text for most elements */
        --text-black: #000000;     /* Black text for light backgrounds */
        --accent-border: #999999;  /* Subtle grey for borders */
    }

    /* Main background - Grant Thornton Purple */
    .stApp {
        background-color: var(--gt-purple-dark);
        color: var(--text-white);
    }

    /* Sidebar background - Dark Grey as requested */
    .st-emotion-cache-vk32no { /* Target sidebar by class */
        background-color: var(--gt-grey-dark); /* Dark Grey */
        color: var(--text-white);
    }
    .st-emotion-cache-1wq0a0j { /* Another sidebar class for general elements */
        background-color: var(--gt-grey-dark);
        color: var(--text-white);
    }
    .st-emotion-cache-16txt4v { /* Sidebar header/title color */
        color: var(--text-white);
    }
    /* "App Control" sidebar title - White as requested */
    .st-emotion-cache-1wq0a0j h2 { /* Targeting the h2 for sidebar title */
        color: var(--text-white);
    }


    /* Header text (H1, H2, H3 etc.) - White for strong contrast */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-white);
    }

    /* General paragraph and list item text - White */
    p, li, div, span {
        color: var(--text-white);
    }

    /* Buttons - Light Grey background, with purple text */
    .stButton > button {
        background-color: var(--gt-grey-light); /* Light Grey accent */
        color: var(--gt-purple-dark); /* Grant Thornton Purple text on button */
        border-radius: 8px;
        border: 1px solid var(--accent-border);
        transition: all 0.2s ease-in-out;
    }
    .stButton > button:hover {
        background-color: var(--text-white); /* White on hover */
        color: var(--gt-purple-dark); /* Grant Thornton Purple text on hover */
        border: 1px solid var(--gt-purple-dark);
    }
    /* Specific: "Refresh Data & Identify Opportunities" button text to black */
    .stButton > button[data-testid="stFormSubmitButton"] {
        color: var(--text-black) !important; /* Force black text */
    }
    /* General button text (ensuring all button text is black) */
    .stButton > button span {
        color: var(--text-black) !important;
    }


    /* Selectbox/Dropdowns - Dark Grey background, Black text inside, White label */
    .st-emotion-cache-13ejs9c { /* Container for selectbox */
        background-color: var(--gt-grey-dark); /* Dark Grey */
        border-radius: 8px;
        border: 1px solid var(--gt-grey-medium); /* Medium Grey border */
    }
    .st-emotion-cache-1wq0a0j.e1tzin5v2 { /* Selectbox options - background */
        background-color: var(--gt-grey-dark);
        color: var(--text-white); /* White text for options in dropdown list */
    }
    .st-emotion-cache-1wq0a0j.e1tzin5v2:hover {
        background-color: var(--gt-grey-medium); /* Slightly lighter grey on hover */
    }
    /* Text color inside the selectbox input area (selected value) - BLACK as requested */
    .st-emotion-cache-1wq0a0j.e1tzin5v2 div[data-baseweb="select"] {
        color: var(--text-black); /* Black text for the selected value */
        background-color: var(--gt-grey-light); /* Light grey background for selected value area */
    }
    .st-emotion-cache-1wq0a0j.e1tzin5v2 input {
        color: var(--text-black); /* Black text inside input for selectbox */
        background-color: var(--gt-grey-light); /* Light grey background for input area */
    }
    /* Dropdown labels (e.g., "Filter by Source:") - White as requested */
    label[data-testid^="stWidgetLabel"] {
        color: var(--text-white);
    }


    /* Text input - Dark Grey background, White text */
    .st-emotion-cache-1c7y2kl { /* Text input container */
        background-color: var(--gt-grey-dark);
        color: var(--text-white);
        border-radius: 8px;
        border: 1px solid var(--gt-grey-medium);
    }
    .st-emotion-cache-1c7y2kl input {
        color: var(--text-white);
    }

    /* Info/Warning boxes - Dark Grey background, White text, Purple border */
    .st-emotion-cache-1c7y2kl { /* General message box container */
        background-color: var(--gt-grey-medium); /* Medium grey for general info/warning */
        color: var(--text-white);
        border-left: 5px solid var(--gt-purple-dark); /* Grant Thornton Purple border */
    }
    /* "About" info box - Grant Thornton Purple background, White text */
    .st-emotion-cache-1c7y2kl[data-testid="stInfo"] { /* Target st.info specifically for About box */
        background-color: var(--gt-purple-dark); /* Grant Thornton Purple as requested */
        color: var(--text-white); /* White text as requested */
        border-left: 5px solid var(--text-white); /* White border for contrast */
    }
    .st-emotion-cache-1c7y2kl[data-testid="stInfo"] p {
        color: var(--text-white); /* Ensure text inside info box is white */
    }


    /* Dataframe styling */
    .st-emotion-cache-cnjsq8 { /* Dataframe container */
        background-color: var(--gt-purple-light); /* Lighter purple for container */
        color: var(--text-white);
        border-radius: 8px;
        border: 1px solid var(--gt-grey-medium);
    }
    .st-emotion-cache-cnjsq8 table {
        background-color: var(--gt-purple-light);
        color: var(--text-white);
    }
    .st-emotion-cache-cnjsq8 th { /* Table headers - Medium Grey background, White text */
        background-color: var(--gt-grey-medium);
        color: var(--text-white);
    }
    .st-emotion-cache-cnjsq8 td { /* Table cells - White text */
        color: var(--text-white);
    }
    .st-emotion-cache-cnjsq8 tr:nth-child(even) { /* Zebra striping - Dark Purple */
        background-color: var(--gt-purple-dark);
    }
    .st-emotion-cache-cnjsq8 tr:nth-child(odd) { /* Zebra striping - Lighter Purple */
        background-color: var(--gt-purple-light);
    }
    .st-emotion-cache-cnjsq8 .header-cell { /* Specific header cell styling */
        color: var(--text-white);
        background-color: var(--gt-grey-medium);
    }

    /* Highlight top 3 rows with Gold, Silver, Bronze */
    .st-emotion-cache-cnjsq8 tbody tr:nth-child(1) {
        background-color: #FFD700 !important; /* Gold */
        color: var(--text-black) !important; /* Black text for readability on gold */
    }
    .st-emotion-cache-cnjsq8 tbody tr:nth-child(1) td {
        color: var(--text-black) !important;
    }

    .st-emotion-cache-cnjsq8 tbody tr:nth-child(2) {
        background-color: #C0C0C0 !important; /* Silver */
        color: var(--text-black) !important; /* Black text for readability on silver */
    }
    .st-emotion-cache-cnjsq8 tbody tr:nth-child(2) td {
        color: var(--text-black) !important;
    }

    .st-emotion-cache-cnjsq8 tbody tr:nth-child(3) {
        background-color: #CD7F32 !important; /* Bronze */
        color: var(--text-white) !important; /* White text for readability on bronze */
    }
    .st-emotion-cache-cnjsq8 tbody tr:nth-child(3) td {
        color: var(--text-white) !important;
    }


    /* Download button text - Black */
    .stDownloadButton > button {
        color: var(--text-black) !important; /* Force black text */
    }
    .stDownloadButton > button span {
        color: var(--text-black) !important;
    }


    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-track {
        background: var(--gt-purple-light);
    }
    ::-webkit-scrollbar-thumb {
        background: var(--gt-grey-light);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: var(--text-white);
    }

</style>
""", unsafe_allow_html=True)


# --- Data Refresh Function ---
def run_pipeline():
    """
    Executes the entire pipeline: scraping, NLP, opportunity identification, storage.
    """
    with st.spinner("Executing data collection & analysis process... This might take a moment."):
        # 1. Run Scraper - Call the function from the imported legislative_scraper module
        latest_legislative_news_df = legislative_scraper.get_latest_legislative_news(current_config=config, filter_by_current_date=False) # Process all recent data

        # 2. NLP Processing
        processed_df = pd.DataFrame()
        if not latest_legislative_news_df.empty:
            processed_df = nlp_processor_instance.process_dataframe(latest_legislative_news_df)
        
        # 3. Opportunity Identification & Scoring
        identified_opportunities_df = pd.DataFrame()
        if not processed_df.empty:
            identified_opportunities_df = opportunity_identifier_instance.identify_and_score_opportunities(processed_df)

        # 4. Save to database
        db_manager_instance.connect()
        db_manager_instance.create_table() # Ensure table is updated (drops and recreates)
        if not processed_df.empty:
            # Ensure processed_df has the opportunity_score and opportunity_type columns
            for col in ['opportunity_score', 'opportunity_type']:
                if col not in processed_df.columns:
                    processed_df[col] = None
            db_manager_instance.insert_opportunities(processed_df)
        db_manager_instance.close()

    st.success("Process completed! Data refreshed.")
    return identified_opportunities_df

# --- Main Application Logic ---
st.header("AI Product Opportunity Identifier 💡")
st.markdown("Discovering new opportunities in tax and economic sectors.")

# Sidebar for options
st.sidebar.title("App Control")
refresh_button = st.sidebar.button("Refresh Data & Identify Opportunities", help="Click to re-run the entire data pipeline and find new opportunities.")
st.sidebar.markdown("---")
st.sidebar.subheader("About")
st.sidebar.info(
    "This application automatically scrapes tax and economic news, processes it with NLP, "
    "identifies potential consulting opportunities, and displays them in an interactive dashboard."
)

# Initialize session state for the button click if not already
if 'refresh_button_clicked' not in st.session_state:
    st.session_state['refresh_button_clicked'] = False

# Logic to trigger pipeline on button click
if refresh_button:
    st.session_state['refresh_button_clicked'] = True
    identified_opportunities_df = run_pipeline()
    st.session_state['last_identified_df'] = identified_opportunities_df # Store for re-runs
else:
    # Load data on initial page load or subsequent non-button refreshes
    if 'last_identified_df' not in st.session_state:
        with st.spinner("Loading initial data from the database..."):
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
st.subheader("Identified Opportunities Overview")

if identified_opportunities_df.empty:
    st.warning("No opportunities found at the moment. Press 'Refresh Data & Identify Opportunities' to start collecting.")
else:
    total_opportunities = len(identified_opportunities_df)
    st.info(f"Total {total_opportunities} opportunities identified. Showing top results.")

    # Search and Filter section
    st.markdown("---")
    st.subheader("Filter & Search Results")
    
    search_query = st.text_input("Search by Title or Keywords:", "")

    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        selected_source = st.selectbox("Filter by Source:", ["All"] + list(identified_opportunities_df['source'].unique()))
    with col_filter2:
        selected_type = st.selectbox("Filter by Opportunity Type:", ["All"] + list(identified_opportunities_df['opportunity_type'].unique()))

    filtered_df = identified_opportunities_df.copy()

    # Apply search filter
    if search_query:
        filtered_df = filtered_df[
            filtered_df['title'].str.contains(search_query, case=False, na=False) |
            filtered_df['keywords'].str.contains(search_query, case=False, na=False)
        ]

    # Apply dropdown filters
    if selected_source != "All":
        filtered_df = filtered_df[filtered_df['source'] == selected_source]
    if selected_type != "All":
        filtered_df = filtered_df[filtered_df['opportunity_type'] == selected_type]

    if filtered_df.empty:
        st.info("No opportunities found matching the selected filters or search query.")
    else:
        # Apply head(10) here to show only the top 10 after filtering
        filtered_df = filtered_df.head(10) # <-- Apply head(10) here

        st.dataframe(
            filtered_df[[
                'title', 'date', 'source', 'opportunity_score', 'opportunity_type', 'url', 'keywords', 'main_topic'
            ]].style.format({'opportunity_score': "{:.1f}"}),
            use_container_width=True,
            hide_index=True, # Corrected argument
            column_config={
                "url": st.column_config.LinkColumn("URL", display_text="Article Link"),
                "date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                "opportunity_score": st.column_config.NumberColumn("Score", help="Importance Score (Higher is better)"),
                "opportunity_type": st.column_config.TextColumn("Opportunity Type"),
                "title": st.column_config.TextColumn("Title", width="large"),
                "source": st.column_config.TextColumn("Source"),
                "keywords": st.column_config.TextColumn("Keywords"),
                "main_topic": st.column_config.TextColumn("Main Topic")
            }
        )
        
        # Download button for filtered data
        csv_data = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Filtered Data as CSV",
            data=csv_data,
            file_name="identified_opportunities.csv",
            mime="text/csv",
            help="Download the currently filtered opportunities as a CSV file."
        )

st.markdown("---")
st.markdown("For more information or technical support, please contact the development team.")
