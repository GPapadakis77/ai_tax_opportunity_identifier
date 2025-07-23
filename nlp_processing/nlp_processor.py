import spacy
import pandas as pd
import os
import sys
from spacy.cli import download as spacy_download # <-- Νέο import

# Προσθήκη του ριζικού φακέλου του project στο PATH για να βρίσκει το config
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config

class NLPProcessor:
    def __init__(self):
        """
        Κατά την αρχικοποίηση, ελέγχουμε αν το μοντέλο υπάρχει.
        Αν δεν υπάρχει, το κατεβάζουμε. Αυτή είναι η πιο σίγουρη μέθοδος.
        """
        model_name = "el_core_news_sm"
        try:
            # Ελέγχουμε αν το μοντέλο είναι ήδη διαθέσιμο
            spacy.load(model_name)
            print(f"Το μοντέλο '{model_name}' βρέθηκε και φορτώθηκε.")
        except OSError:
            # Αν δεν βρεθεί, το κατεβάζουμε
            print(f"Το μοντέλο '{model_name}' δεν βρέθηκε. Γίνεται λήψη...")
            spacy_download(model_name)
            print("Η λήψη ολοκληρώθηκε.")
        
        # Τώρα το φορτώνουμε με ασφάλεια
        self.nlp = spacy.load(model_name)
        self.tax_keywords = config.TAX_KEYWORDS

    def process_text(self, text):
        """
        Επεξεργάζεται ένα κείμενο χρησιμοποιώντας spaCy για την εξαγωγή λέξεων-κλειδιών,
        οντοτήτων (NER) και του βασικού θέματος.
        """
        if not text or not isinstance(text, str):
            return [], [], None

        doc = self.nlp(text)
        
        # Εξαγωγή Λέξεων-Κλειδιών
        keywords = []
        for token in doc:
            if token.pos_ in ["NOUN", "PROPN", "ADJ", "VERB"] and not token.is_stop and not token.is_punct:
                keywords.append(token.lemma_.lower())
        
        for keyword in self.tax_keywords:
            if keyword in text.lower() and keyword not in keywords:
                keywords.append(keyword)

        keywords = sorted(list(set(keywords)))

        # Αναγνώριση Οντοτήτων (NER)
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        
        # Βασική Θεματική Ανάλυση
        main_topic = "Γενικό Οικονομικό Θέμα"
        if any(kw in keywords for kw in ["φορολογία", "φορολογικός", "φόρος"]):
            main_topic = "Φορολογική Πολιτική/Νομοθεσία"
        elif "ααδε" in keywords:
            main_topic = "ΑΑΔΕ / Εφαρμογή Νόμων"
        elif any(kw in keywords for kw in ["πρόγραμμα", "εσπα", "ανάπτυξη", "επιδότηση", "κίνητρα"]):
            main_topic = "Αναπτυξιακά Προγράμματα / Κίνητρα"
        elif any(kw in keywords for kw in ["προϋπολογισμός", "δαπάνες"]):
            main_topic = "Δημοσιονομική Πολιτική"
        elif any(kw in keywords for kw in ["χρέος", "οφειλές"]):
            main_topic = "Διαχείριση Χρέους"
            
        return keywords, entities, main_topic

    def process_dataframe(self, df):
        """
        Επεξεργάζεται ένα DataFrame και προσθέτει στήλες με τα αποτελέσματα του NLP.
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

# ... (ο υπόλοιπος κώδικας δοκιμής παραμένει ίδιος) ...