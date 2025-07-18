import pandas as pd
import os
import sys
import importlib

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config
importlib.reload(config)

class OpportunityIdentifier:
    def __init__(self):
        self.tax_opportunity_keywords = config.TAX_KEYWORDS
        self.incentive_keywords = ["κίνητρα", "επιδότηση", "ΕΣΠΑ", "πρόγραμμα", "χρηματοδότηση", "ανάπτυξη", "επένδυση", "ταμείο", "ανάκαμψη", "σχέδιο"] # Expanded
        self.debt_keywords = ["χρέος", "οφειλές", "ρύθμιση", "πλειστηριασμός", "εξωδικαστικός", "δάνειο", "τράπεζα"] # Expanded
        self.aade_keywords = ["ΑΑΔΕ", "MyDATA", "φορολογική δήλωση", "πλατφόρμα", "προθεσμία", "ελεγκτές", "ψηφιακός", "υπηρεσία", "ανακοίνωση"] # Expanded
        self.law_change_keywords = ["νόμος", "διάταξη", "τροποποίηση", "νομοσχέδιο", "ΦΕΚ", "υπουργική απόφαση", "ισχύς", "αλλαγή", "νέος"] # Expanded

        # Adjusted scoring rules for broader inclusion and better differentiation
        self.scoring_rules = {
            "main_topic:Φορολογική Πολιτική/Νομοθεσία": 6, # Increased score
            "main_topic:Αναπτυξιακά Προγράμματα": 5,     # Increased score
            "main_topic:Δημοσιονομική Πολιτική": 4,
            "main_topic:Διαχείριση Ιδιωτικού/Δημόσιου Χρέους": 4,
            "keyword_match:law_change": 5,              # Increased score
            "keyword_match:incentive": 5,               # Increased score
            "keyword_match:debt": 4,
            "keyword_match:aade": 4,
            "keyword_match:tax_opportunity": 3,         # Increased base score for any tax keyword
            "entity_ORG:ΑΑΔΕ": 6,                       # Increased score for direct AADE mention
            "entity_ORG:Υπουργείο Οικονομικών": 5,      # Increased score
            "entity_ORG:Ελληνικό Δημόσιο": 4,
            "entity_LOC:Ελλάδα": 1,
            "general_news_with_keywords": 1             # New rule: give a base score if any tax keyword is present
        }

    def _calculate_score(self, row):
        """Calculates a score for each opportunity based on the defined rules."""
        score = 0
        keywords = row['keywords'].split(', ') if pd.notna(row['keywords']) and row['keywords'] else []
        entities = eval(row['entities']) if pd.notna(row['entities']) and row['entities'] else []
        main_topic = row['main_topic'] if pd.notna(row['main_topic']) else None

        # Score based on main_topic
        if main_topic:
            rule_key = f"main_topic:{main_topic}"
            score += self.scoring_rules.get(rule_key, 0)

        # Score based on specific keyword matches
        found_specific_keyword = False
        for kw in keywords:
            if kw in self.law_change_keywords:
                score += self.scoring_rules.get("keyword_match:law_change", 0)
                found_specific_keyword = True
            if kw in self.incentive_keywords:
                score += self.scoring_rules.get("keyword_match:incentive", 0)
                found_specific_keyword = True
            if kw in self.debt_keywords:
                score += self.scoring_rules.get("keyword_match:debt", 0)
                found_specific_keyword = True
            if kw in self.aade_keywords:
                score += self.scoring_rules.get("keyword_match:aade", 0)
                found_specific_keyword = True
            
            # General tax opportunity keywords
            if kw in self.tax_opportunity_keywords:
                score += self.scoring_rules.get("keyword_match:tax_opportunity", 0)
                found_specific_keyword = True # Even general tax keywords count as finding something

        # Score based on entities
        for ent_text, ent_label in entities:
            if ent_label == 'ORG':
                if "ΑΑΔΕ" in ent_text:
                    score += self.scoring_rules.get("entity_ORG:ΑΑΔΕ", 0)
                    found_specific_keyword = True
                elif "Υπουργείο Οικονομικών" in ent_text:
                    score += self.scoring_rules.get("entity_ORG:Υπουργείο Οικονομικών", 0)
                    found_specific_keyword = True
                elif "Ελληνικό Δημόσιο" in ent_text:
                    score += self.scoring_rules.get("entity_ORG:Ελληνικό Δημόσιο", 0)
                    found_specific_keyword = True
            elif ent_label == 'LOC' and "Ελλάδα" in ent_text:
                score += self.scoring_rules.get("entity_LOC:Ελλάδα", 0)
                found_specific_keyword = True

        # New rule: If any tax keyword was found (even general ones) and no specific topic was assigned yet, give a base score
        if score == 0 and any(kw in keywords for kw in self.tax_opportunity_keywords):
             score += self.scoring_rules.get("general_news_with_keywords", 0)


        return score

    def _assign_opportunity_type(self, row):
        """Assigns an opportunity type based on keywords and topic."""
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
        elif any(kw in keywords for kw in self.tax_opportunity_keywords): # General tax news
            return "Γενική Φορολογική Είδηση"
        else:
            return "Άγνωστος Τύπος"

    def identify_and_score_opportunities(self, df):
        """
        Identifies and scores opportunities in a DataFrame.
        Adds 'opportunity_score' and 'opportunity_type' columns.
        """
        if df.empty:
            return df

        df['opportunity_score'] = df.apply(self._calculate_score, axis=1)
        df['opportunity_type'] = df.apply(self._assign_opportunity_type, axis=1)

        # Filter for opportunities with a score > 0
        opportunities_df = df[df['opportunity_score'] > 0].copy()
        
        # Sort opportunities by score (descending)
        opportunities_df = opportunities_df.sort_values(by='opportunity_score', ascending=False)

        return opportunities_df

# This block is for direct execution of the script, not when imported.
if __name__ == "__main__":
    print("This script is meant to be imported and called from the main application.")
    print("Please run the Streamlit/Gradio app to execute the functionality.")