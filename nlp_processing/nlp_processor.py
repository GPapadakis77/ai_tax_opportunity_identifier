# nlp_processing/nlp_processor.py

import spacy
import pandas as pd
import os
import sys

# Προσθήκη του ριζικού φακέλου του project στο PATH για να βρίσκει το config
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config

# Φόρτωση του ελληνικού μοντέλου της spaCy
try:
    nlp = spacy.load("el_core_news_sm")
    print("Το ελληνικό μοντέλο spaCy φορτώθηκε επιτυχώς.")
except Exception as e:
    print(f"Σφάλμα φόρτωσης ελληνικού μοντέλου spaCy: {e}")
    print("Βεβαιωθείτε ότι το 'el_core_news_sm' έχει κατέβει με την εντολή: !python -m spacy download el_core_news_sm")
    nlp = None # Ορίζουμε nlp ως None αν η φόρτωση αποτύχει

class NLPProcessor:
    def __init__(self):
        if nlp is None:
            raise RuntimeError("Το μοντέλο spaCy δεν φορτώθηκε. Δεν είναι δυνατή η εκκίνηση του NLPProcessor.")
        self.nlp = nlp
        self.tax_keywords = config.TAX_KEYWORDS # Χρησιμοποιούμε τα keywords από το config

    def process_text(self, text):
        """
        Επεξεργάζεται ένα κείμενο χρησιμοποιώντας spaCy για:
        - Εξαγωγή λέξεων-κλειδιών (βάσει προκαθορισμένων και NER)
        - Αναγνώριση οντοτήτων (NER)
        - Συνοπτική περιγραφή θέματος (πολύ βασική προς το παρόν)
        """
        if not text:
            return [], [], None

        doc = self.nlp(text)
        
        # 1. Εξαγωγή Λέξεων-Κλειδιών: Βρίσκουμε ουσιαστικά, ρήματα, επίθετα
        # και τα φιλτράρουμε αν περιέχονται στα TAX_KEYWORDS
        keywords = []
        for token in doc:
            # Προσθέτουμε σημαντικές λέξεις-κλειδιά (π.χ. ουσιαστικά, επίθετα, ρήματα, κύρια ονόματα)
            if token.pos_ in ["NOUN", "PROPN", "ADJ", "VERB"] and not token.is_stop and not token.is_punct:
                keywords.append(token.lemma_.lower()) # Χρησιμοποιούμε lemma για τη βασική μορφή της λέξης
        
        # Επίσης, προσθέτουμε λέξεις-κλειδιά που ταιριάζουν με το config.TAX_KEYWORDS
        # (ακόμα και αν είναι stop words, γιατί φορολογικοί όροι μπορεί να είναι)
        for keyword in self.tax_keywords:
            if keyword in text.lower() and keyword not in keywords:
                keywords.append(keyword)

        # Αφαίρεση διπλοτύπων και ταξινόμηση
        keywords = sorted(list(set(keywords)))

        # 2. Αναγνώριση Οντοτήτων (Named Entity Recognition - NER)
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        
        # 3. Βασική Θεματική Ανάλυση (placeholder για πιο σύνθετη λογική)
        # Για αρχή, μπορούμε να βασιστούμε στις πιο συχνές λέξεις-κλειδιά
        # ή να ελέγξουμε για συγκεκριμένες φράσεις/έννοιες
        main_topic = None
        if "φορολογία" in keywords or "φορολογικός" in keywords:
            main_topic = "Φορολογική Πολιτική/Νομοθεσία"
        elif "ΑΑΔΕ" in keywords:
            main_topic = "ΑΑΔΕ / Εφαρμογή Νόμων"
        elif "πρόγραμμα" in keywords or "ΕΣΠΑ" in keywords or "ανάπτυξη" in keywords:
            main_topic = "Αναπτυξιακά Προγράμματα"
        elif "προϋπολογισμός" in keywords or "δαπάνες" in keywords:
            main_topic = "Δημοσιονομική Πολιτική"
        elif "χρέος" in keywords or "οφειλές" in keywords:
            main_topic = "Διαχείριση Ιδιωτικού/Δημόσιου Χρέους"
        
        # Αυτό μπορεί να γίνει πιο εξελιγμένο με ταξινόμηση κειμένου (text classification)
        # σε μεταγενέστερο στάδιο.

        return keywords, entities, main_topic

    def process_dataframe(self, df):
        """
        Επεξεργάζεται ένα DataFrame με κείμενα και προσθέτει στήλες NLP.
        Υποθέτει ότι το DataFrame έχει στήλη 'title' (και ενδεχομένως 'url' για πλήρες κείμενο).
        """
        if df.empty:
            return df

        processed_data = []
        for index, row in df.iterrows():
            # Για την πρώτη φάση, θα χρησιμοποιήσουμε μόνο τον τίτλο ως κείμενο για NLP
            # Σε μελλοντική φάση, θα κατεβάζουμε και το πλήρες κείμενο από το URL
            text_to_process = row['title'] + " " + (row['description'] if 'description' in row and row['description'] else "")
            
            keywords, entities, main_topic = self.process_text(text_to_process)
            
            # Δημιουργούμε ένα νέο dictionary για κάθε γραμμή με τα NLP αποτελέσματα
            # και τα προσθέτουμε στα αρχικά δεδομένα της γραμμής.
            processed_row = row.to_dict() # Μετατρέπουμε τη σειρά σε dictionary
            processed_row['keywords'] = ", ".join(keywords) # Μετατροπή λίστας σε string
            processed_row['entities'] = str(entities)      # Μετατροπή λίστας από tuples σε string
            processed_row['main_topic'] = main_topic
            
            processed_data.append(processed_row)
        
        return pd.DataFrame(processed_data)

# Λειτουργία δοκιμής του module
if __name__ == "__main__":
    print("Εκτέλεση του nlp_processor.py απευθείας (για δοκιμή).")
    
    # Δημιουργία ενός δοκιμαστικού DataFrame
    test_df = pd.DataFrame({
        'title': [
            'Νέος νόμος για τη φορολογία ακινήτων τέθηκε σε ισχύ',
            'Ανακοίνωση ΑΑΔΕ για MyDATA: Παράταση προθεσμίας',
            'Επένδυση σε πράσινη ενέργεια: Νέα κίνητρα ΕΣΠΑ',
            'Συνάντηση Υπουργού Οικονομικών για το δημόσιο χρέος'
        ],
        'url': [
            'http://example.com/law1',
            'http://example.com/aade1',
            'http://example.com/espa1',
            'http://example.com/debt1'
        ],
        'date': [
            pd.to_datetime('2025-07-08').date(),
            pd.to_datetime('2025-07-07').date(),
            pd.to_datetime('2025-07-06').date(),
            pd.to_datetime('2025-07-05').date()
        ],
        'source': ['TestNews', 'TestNews', 'TestNews', 'TestNews']
    })

    try:
        nlp_processor = NLPProcessor()
        processed_df = nlp_processor.process_dataframe(test_df)
        print("\nΑποτελέσματα NLP:")
        print(processed_df[['title', 'keywords', 'entities', 'main_topic']].head())
    except RuntimeError as e:
        print(f"Δεν ήταν δυνατή η εκτέλεση του NLPProcessor: {e}")