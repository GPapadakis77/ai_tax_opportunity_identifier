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
        self.all_keywords = [kw.lower() for kw in config.TAX_KEYWORDS]
        self.high_priority_keywords = ["επιδότηση", "κίνητρα", "ΕΣΠΑ", "χρηματοδότηση", "νέο νομοσχέδιο", "τροποποίηση"]
        self.medium_priority_keywords = ["ΑΑΔΕ", "MyDATA", "φορολογικές δηλώσεις", "ΦΠΑ", "επένδυση", "εξαγορά", "διαγωνισμός"]

    def _calculate_score(self, row):
        score = 0
        text_content = (str(row.get('title', '')) + ' ' + str(row.get('full_text', ''))).lower()

        found_any_keyword = any(kw in text_content for kw in self.all_keywords)
        
        if not found_any_keyword:
            return 0
        
        score = 1.0

        if any(kw in text_content for kw in self.high_priority_keywords):
            score += 3.0
        
        if any(kw in text_content for kw in self.medium_priority_keywords):
            score += 1.5
        
        if row.get('source') == 'Ministry of Finance':
            score += 1.0
            
        return score

    def _assign_opportunity_type(self, text_content):
        text_content = text_content.lower()
        if any(kw in text_content for kw in self.high_priority_keywords):
            return "Κίνητρα / Νομοθεσία"
        if any(kw in text_content for kw in self.medium_priority_keywords):
            return "Ενημέρωση ΑΑΔΕ / Επένδυση"
        return "Γενική Οικονομική Είδηση"

    def identify_and_score_opportunities(self, df):
        if df.empty:
            return df

        df['opportunity_score'] = df.apply(self._calculate_score, axis=1)
        opportunities_df = df[df['opportunity_score'] > 0].copy()

        if not opportunities_df.empty:
            opportunities_df['opportunity_type'] = opportunities_df.apply(
                lambda row: self._assign_opportunity_type(
                    str(row.get('title', '')) + ' ' + str(row.get('full_text', ''))
                ), 
                axis=1
            )
        
        opportunities_df = opportunities_df.sort_values(by='opportunity_score', ascending=False)
        return opportunities_df