# opportunity_identification/opportunity_identifier.py

import pandas as pd
import os
import sys

# Προσθήκη του ριζικού φακέλου του project στο PATH για να βρίσκει το config
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config

class OpportunityIdentifier:
    def __init__(self):
        # Ορίζουμε κανόνες και λέξεις-κλειδιά για την αναγνώριση ευκαιριών
        # Αυτές οι λίστες μπορούν να εμπλουτιστούν και να γίνουν πιο σύνθετες
        self.tax_opportunity_keywords = config.TAX_KEYWORDS # Χρησιμοποιούμε τα ίδια keywords από το config
        self.incentive_keywords = ["κίνητρα", "επιδότηση", "ΕΣΠΑ", "πρόγραμμα", "χρηματοδότηση", "ανάπτυξη", "επένδυση"]
        self.debt_keywords = ["χρέος", "οφειλές", "ρύθμιση", "πλειστηριασμός", "εξωδικαστικός"]
        self.aade_keywords = ["ΑΑΔΕ", "MyDATA", "φορολογική δήλωση", "πλατφόρμα", "προθεσμία", "ελεγκτές"]
        self.law_change_keywords = ["νόμος", "διάταξη", "τροποποίηση", "νομοσχέδιο", "ΦΕΚ", "υπουργική απόφαση"]

        # Ορίζουμε κανόνες βαθμολόγησης
        self.scoring_rules = {
            "main_topic:Φορολογική Πολιτική/Νομοθεσία": 5,
            "main_topic:Αναπτυξιακά Προγράμματα": 4,
            "main_topic:Δημοσιονομική Πολιτική": 3,
            "main_topic:Διαχείριση Ιδιωτικού/Δημόσιου Χρέους": 3,
            "keyword_match:law_change": 4,
            "keyword_match:incentive": 4,
            "keyword_match:debt": 3,
            "keyword_match:aade": 3,
            "keyword_match:tax_opportunity": 2, # Γενικά φορολογικά keywords
            "entity_ORG:ΑΑΔΕ": 5,
            "entity_ORG:Υπουργείο Οικονομικών": 4,
            "entity_ORG:Ελληνικό Δημόσιο": 3,
            "entity_LOC:Ελλάδα": 1 # Γενική τοποθεσία
        }

    def _calculate_score(self, row):
        """Υπολογίζει μια βαθμολογία για κάθε ευκαιρία βάσει των κανόνων."""
        score = 0
        keywords = row['keywords'].split(', ') if pd.notna(row['keywords']) and row['keywords'] else []
        entities = eval(row['entities']) if pd.notna(row['entities']) and row['entities'] else [] # eval() για να μετατρέψει το string σε λίστα tuples
        main_topic = row['main_topic'] if pd.notna(row['main_topic']) else None

        # Βαθμολόγηση βάσει main_topic
        if main_topic:
            rule_key = f"main_topic:{main_topic}"
            score += self.scoring_rules.get(rule_key, 0)

        # Βαθμολόγηση βάσει λέξεων-κλειδιών
        for kw in keywords:
            if kw in self.law_change_keywords:
                score += self.scoring_rules.get("keyword_match:law_change", 0)
            if kw in self.incentive_keywords:
                score += self.scoring_rules.get("keyword_match:incentive", 0)
            if kw in self.debt_keywords:
                score += self.scoring_rules.get("keyword_match:debt", 0)
            if kw in self.aade_keywords:
                score += self.scoring_rules.get("keyword_match:aade", 0)
            if kw in self.tax_opportunity_keywords:
                score += self.scoring_rules.get("keyword_match:tax_opportunity", 0)
        
        # Βαθμολόγηση βάσει οντοτήτων
        for ent_text, ent_label in entities:
            if ent_label == 'ORG':
                if "ΑΑΔΕ" in ent_text:
                    score += self.scoring_rules.get("entity_ORG:ΑΑΔΕ", 0)
                elif "Υπουργείο Οικονομικών" in ent_text:
                    score += self.scoring_rules.get("entity_ORG:Υπουργείο Οικονομικών", 0)
                elif "Ελληνικό Δημόσιο" in ent_text:
                    score += self.scoring_rules.get("entity_ORG:Ελληνικό Δημόσιο", 0)
            elif ent_label == 'LOC' and "Ελλάδα" in ent_text:
                score += self.scoring_rules.get("entity_LOC:Ελλάδα", 0)

        return score

    def _assign_opportunity_type(self, row):
        """Αναθέτει έναν τύπο ευκαιρίας βάσει των λέξεων-κλειδιών και του θέματος."""
        keywords = row['keywords'].split(', ') if pd.notna(row['keywords']) and row['keywords'] else []
        main_topic = row['main_topic'] if pd.notna(row['main_topic']) else None

        if main_topic == "Φορολογική Πολιτική/Νομοθεσία" or any(kw in keywords for kw in self.law_change_keywords):
            return "Αλλαγή Φορολογικής Νομοθεσίας"
        elif main_topic == "Αναπτυξιακά Προγράμματα" or any(kw in keywords for kw in self.incentive_keywords):
            return "Αναπτυξιακά / Κίνητρα / Επιδότηση"
        elif main_topic == "Διαχείριση Ιδιωτικού/Δημόσιου Χρέους" or any(kw in keywords for kw in self.debt_keywords):
            return "Διαχείριση Χρέους / Ρυθμίσεις"
        elif any(kw in keywords for kw in self.aade_keywords):
            return "Ανακοίνωση / Ενημέρωση ΑΑΔΕ"
        elif main_topic == "Δημοσιονομική Πολιτική":
            return "Δημοσιονομική Πολιτική"
        elif any(kw in keywords for kw in self.tax_opportunity_keywords):
            return "Γενική Φορολογική Είδηση"
        else:
            return "Άγνωστος Τύπος"

    def identify_and_score_opportunities(self, df):
        """
        Εντοπίζει και βαθμολογεί ευκαιρίες σε ένα DataFrame.
        Προσθέτει τις στήλες 'opportunity_score' και 'opportunity_type'.
        """
        if df.empty:
            return df

        # Εφαρμόζουμε τις συναρτήσεις σε κάθε γραμμή του DataFrame
        df['opportunity_score'] = df.apply(self._calculate_score, axis=1)
        df['opportunity_type'] = df.apply(self._assign_opportunity_type, axis=1)

        # Φιλτράρουμε για ευκαιρίες με βαθμολογία > 0 ή συγκεκριμένο τύπο (π.χ. όχι 'Άγνωστος Τύπος')
        # Μπορείτε να προσαρμόσετε αυτό το όριο.
        opportunities_df = df[df['opportunity_score'] > 0].copy()
        
        # Ταξινόμηση των ευκαιριών με βάση τη βαθμολογία (φθίνουσα)
        opportunities_df = opportunities_df.sort_values(by='opportunity_score', ascending=False)

        return opportunities_df

# Λειτουργία δοκιμής του module
if __name__ == "__main__":
    print("Εκτέλεση του opportunity_identifier.py απευθείας (για δοκιμή).")
    
    # Δημιουργία ενός δοκιμαστικού DataFrame με NLP πεδία
    test_df_nlp = pd.DataFrame({
        'id': ['test_opp_1', 'test_opp_2', 'test_opp_3', 'test_opp_4', 'test_opp_5'],
        'title': [
            'Νέος νόμος για τη φορολογία ακινήτων τέθηκε σε ισχύ',
            'Ανακοίνωση ΑΑΔΕ για MyDATA: Παράταση προθεσμίας',
            'Επένδυση σε πράσινη ενέργεια: Νέα κίνητρα ΕΣΠΑ',
            'Συνάντηση Υπουργού Οικονομικών για το δημόσιο χρέος',
            'Γενική είδηση για την οικονομία'
        ],
        'url': [
            'http://example.com/law1',
            'http://example.com/aade1',
            'http://example.com/espa1',
            'http://example.com/debt1',
            'http://example.com/general'
        ],
        'date': [
            pd.to_datetime('2025-07-08').date(),
            pd.to_datetime('2025-07-07').date(),
            pd.to_datetime('2025-07-06').date(),
            pd.to_datetime('2025-07-05').date(),
            pd.to_datetime('2025-07-04').date()
        ],
        'source': ['TestNews', 'TestNews', 'TestNews', 'TestNews', 'TestNews'],
        'keywords': [
            'νόμος, φορολογία, ακίνητο, ισχύς',
            'ΑΑΔΕ, MyDATA, παράταση, προθεσμία',
            'επένδυση, πράσινος, ενέργεια, κίνητρο, ΕΣΠΑ',
            'υπουργός, οικονομικός, δημόσιος, χρέος',
            'οικονομία, γενικός, είδηση'
        ],
        'entities': [
            "[('ακινήτων', 'ORG')]",
            "[('ΑΑΔΕ', 'ORG'), ('MyDATA', 'ORG')]",
            "[('ΕΣΠΑ', 'ORG')]",
            "[('Υπουργού Οικονομικών', 'ORG')]",
            "[]"
        ],
        'main_topic': [
            'Φορολογική Πολιτική/Νομοθεσία',
            None, # Έστω ότι δεν βρέθηκε main_topic από NLP
            'Αναπτυξιακά Προγράμματα',
            'Δημοσιονομική Πολιτική',
            None
        ]
    })

    try:
        identifier = OpportunityIdentifier()
        identified_opportunities_df = identifier.identify_and_score_opportunities(test_df_nlp)
        
        print("\nΕντοπισμένες και Βαθμολογημένες Ευκαιρίες:")
        print(identified_opportunities_df[['title', 'opportunity_score', 'opportunity_type', 'keywords', 'main_topic']].head(10))
        print(f"\nΣυνολικά {len(identified_opportunities_df)} ευκαιρίες εντοπίστηκαν.")
    except Exception as e:
        print(f"Σφάλμα κατά την εκτέλεση του OpportunityIdentifier: {e}")