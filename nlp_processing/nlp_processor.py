import spacy
import pandas as pd
import os
import sys

# Add the project root to the PATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config

class NLPProcessor:
    def __init__(self):
        """
        Loads the spaCy model, assuming it's already installed via requirements.txt.
        This is the correct and stable method for Streamlit Cloud.
        """
        model_name = "el_core_news_sm"
        try:
            self.nlp = spacy.load(model_name)
            print(f"Model '{model_name}' loaded successfully.")
        except OSError:
            print(f"Failed to load model '{model_name}'. Make sure it's in your requirements.txt.")
            # Re-raising the error is important to stop the app if the model is missing.
            raise
        
        self.tax_keywords = config.TAX_KEYWORDS

    def process_text(self, text):
        """
        Processes a single string of text using spaCy.
        """
        if not text or not isinstance(text, str):
            return [], [], None

        doc = self.nlp(text)
        
        # Keyword Extraction
        keywords = []
        for token in doc:
            if token.pos_ in ["NOUN", "PROPN", "ADJ", "VERB"] and not token.is_stop and not token.is_punct:
                keywords.append(token.lemma_.lower())
        
        for keyword in self.tax_keywords:
            if keyword in text.lower() and keyword not in keywords:
                keywords.append(keyword)

        keywords = sorted(list(set(keywords)))

        # Named Entity Recognition (NER)
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        
        # Basic Topic Analysis
        main_topic = "General Economic Topic"
        if any(kw in keywords for kw in ["φορολογία", "φορολογικός", "φόρος"]):
            main_topic = "Tax Policy/Legislation"
        elif "ααδε" in keywords:
            main_topic = "AADE / Law Enforcement"
        elif any(kw in keywords for kw in ["πρόγραμμα", "εσπα", "ανάπτυξη", "επιδότηση", "κίνητρα"]):
            main_topic = "Development Programs / Incentives"
            
        return keywords, entities, main_topic

    def process_dataframe(self, df):
        """
        Processes a DataFrame, adding columns with NLP results.
        """
        if df.empty:
            return df

        processed_data = []
        for index, row in df.iterrows():
            text_to_process = row.get('title', '') + " " + (row.get('description', '') or "")
            keywords, entities, main_topic = self.process_text(text_to_process)
            
            processed_row = row.to_dict()
            processed_row['keywords'] = ", ".join(keywords)
            processed_row['entities'] = str(entities)
            processed_row['main_topic'] = main_topic
            
            processed_data.append(processed_row)
        
        return pd.DataFrame(processed_data)