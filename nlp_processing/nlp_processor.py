import spacy
import pandas as pd
import os
import sys
import el_core_news_sm  # <-- Σημαντικό import για τη σωστή φόρτωση του μοντέλου

# Προσθήκη του ριζικού φακέλου του project στο PATH για να βρίσκει το config
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config

class NLPProcessor:
    def __init__(self):
        """
        Κατά την αρχικοποίηση, φορτώνουμε το μοντέλο spaCy.
        Αυτή η μέθοδος είναι πιο αξιόπιστη από τη φόρτωση σε καθολικό επίπεδο.
        """
        try:
            # Φορτώνουμε το μοντέλο απευθείας από το εγκατεστημένο πακέτο
            self.nlp = el_core_news_sm.load()
            print("Το ελληνικό μοντέλο spaCy φορτώθηκε επιτυχώς μέσα από τον NLPProcessor.")
        except Exception as e:
            print(f"Σφάλμα φόρτωσης ελληνικού μοντέλου spaCy: {e}")
            raise RuntimeError("Το μοντέλο spaCy δεν φορτώθηκε. Δεν είναι δυνατή η εκκίνηση του NLPProcessor.")
        
        self.tax_keywords = config.TAX_KEYWORDS

    def process_text(self, text):
        """
        Επεξεργάζεται ένα κείμενο χρησιμοποιώντας spaCy για την εξαγωγή λέξεων-κλειδιών,
        οντοτήτων (NER) και του βασικού θέματος.
        """
        if not text or not isinstance(text, str):
            return [], [], None

        doc = self.nlp(text)
        
        # 1. Εξαγωγή Λέξεων-Κλειδιών
        keywords = []
        for token in doc:
            if token.pos_ in ["NOUN", "PROPN", "ADJ", "VERB"] and not token.is_stop and not token.is_punct:
                keywords.append(token.lemma_.lower())
        
        for keyword in self.tax_keywords:
            if keyword in text.lower() and keyword not in keywords:
                keywords.append(keyword)

        keywords = sorted(list(set(keywords)))

        # 2. Αναγνώριση Οντοτήτων (NER)
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        
        # 3. Βασική Θεματική Ανάλυση
        main_topic = "Γενικό Οικονομικό Θέμα" # Προεπιλεγμένη τιμή
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

# Λειτουργία δοκιμής του module
if __name__ == "__main__":
    print("Εκτέλεση του nlp_processor.py απευθείας (για δοκιμή).")
    
    test_df = pd.DataFrame({
        'title': [
            'Νέος νόμος για τη φορολογία ακινήτων τέθηκε σε ισχύ',
            'Ανακοίνωση ΑΑΔΕ για MyDATA: Παράταση προθεσμίας',
            'Επένδυση σε πράσινη ενέργεια: Νέα κίνητρα ΕΣΠΑ',
            'Συνάντηση Υπουργού Οικονομικών για το δημόσιο χρέος'
        ],
        'description': ['Περιγραφή 1', 'Περιγραφή 2', '', 'Περιγραφή 4'],
        'url': ['http://example.com/law1', 'http://example.com/aade1', 'http://example.com/espa1', 'http://example.com/debt1'],
        'date': [pd.to_datetime('2025-07-08').date(), pd.to_datetime('2025-07-07').date(), pd.to_datetime('2025-07-06').date(), pd.to_datetime('2025-07-05').date()],
        'source': ['TestNews', 'TestNews', 'TestNews', 'TestNews']
    })

    try:
        nlp_processor = NLPProcessor()
        processed_df = nlp_processor.process_dataframe(test_df)
        print("\nΑποτελέσματα NLP:")
        print(processed_df[['title', 'keywords', 'entities', 'main_topic']].head())
    except RuntimeError as e:
        print(f"Δεν ήταν δυνατή η εκτέλεση του NLPProcessor: {e}")