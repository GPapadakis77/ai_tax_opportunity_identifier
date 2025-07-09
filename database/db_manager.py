# database/db_manager.py

import sqlite3
import pandas as pd
import os
import sys

# Add the project root to the PATH to locate the config module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config

class DBManager:
    def __init__(self, db_name=config.DATABASE_NAME):
        self.db_path = os.path.join(project_root, 'data', db_name)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = None

    def connect(self):
        """Connects to the database."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            print(f"Successfully connected to the database: {self.db_path}")
            return self.conn
        except sqlite3.Error as e:
            print(f"Error connecting to the database: {e}")
            return None

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            print("Database connection closed.")

    def create_table(self):
        """
        Creates the table for AI opportunities.
        Drops the table if it already exists to ensure schema is always up-to-date.
        """
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        # --- NEW ADDITION: Drop table if it exists ---
        cursor.execute("DROP TABLE IF EXISTS opportunities;")
        print("Existing 'opportunities' table dropped (if it existed).")
        # --- END NEW ADDITION ---

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS opportunities (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                date DATE,
                source TEXT,
                full_text TEXT,      -- Will be populated later
                keywords TEXT,       -- NLP result
                entities TEXT,       -- NLP result
                main_topic TEXT,     -- NLP result
                sentiment TEXT,      -- Will be populated later
                opportunity_score REAL, -- New: Opportunity scoring result (REAL for numbers)
                opportunity_type TEXT,  -- New: Type of opportunity
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
        print("The 'opportunities' table has been created (or re-created) with the latest schema.")

    def insert_opportunities(self, df):
        """
        Inserts or updates opportunities from a DataFrame into the table,
        including NLP and opportunity results.
        """
        if df.empty:
            print("No data to insert into the database.")
            return

        if not self.conn:
            self.connect()

        df_copy = df.copy()
        if 'date' in df_copy.columns:
            df_copy['date'] = df_copy['date'].astype(str) # Convert to string (YYYY-MM-DD)

        # Define all columns to match the table schema for insertion
        # Ensure all columns expected by the table are present in the DataFrame.
        # Fill missing ones with None, so the INSERT OR REPLACE works.
        all_table_columns = [
            'id', 'title', 'url', 'date', 'source', 'full_text', 'keywords', 
            'entities', 'main_topic', 'sentiment', 'opportunity_score', 'opportunity_type'
        ]
        
        # Prepare data by ensuring all columns are present and in correct order
        data_to_insert_or_update = []
        for index, row in df_copy.iterrows():
            row_data = [row.get(col) for col in all_table_columns]
            data_to_insert_or_update.append(row_data)

        cursor = self.conn.cursor()
        
        # Use INSERT OR REPLACE to either insert new rows or replace existing ones by 'id'
        # This effectively updates the row if 'id' exists.
        try:
            cursor.executemany(f"""
                INSERT OR REPLACE INTO opportunities (
                    id, title, url, date, source, full_text, keywords, entities, main_topic, sentiment, opportunity_score, opportunity_type
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data_to_insert_or_update)
            self.conn.commit()
            print(f"Insertion/update of {len(df)} opportunities completed in the database.")
        except sqlite3.Error as e:
            print(f"Error during bulk insert/update: {e}")
            self.conn.rollback() # Rollback changes if an error occurs

    def fetch_all_opportunities(self):
        """Retrieves all opportunities from the database."""
        if not self.conn:
            self.connect()
        
        df = pd.read_sql_query("SELECT * FROM opportunities ORDER BY date DESC, added_date DESC", self.conn)
        
        # Convert 'date' column to datetime objects
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
        
        # Ensure 'opportunity_score' is numeric for sorting/filtering
        if 'opportunity_score' in df.columns:
            df['opportunity_score'] = pd.to_numeric(df['opportunity_score'], errors='coerce')
        
        return df

    def get_opportunity_by_id(self, oid):
        """Retrieves an opportunity by its ID."""
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM opportunities WHERE id = ?", (oid,))
        row = cursor.fetchone()
        if row:
            columns = [description[0] for description in cursor.description]
            df = pd.DataFrame([row], columns=columns)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
            if 'opportunity_score' in df.columns:
                df['opportunity_score'] = pd.to_numeric(df['opportunity_score'], errors='coerce')
            return df
        return pd.DataFrame()

# Test function for the module (if executed directly)
if __name__ == "__main__":
    print("Running db_manager.py directly (for testing).")
    db_manager = DBManager()
    db_manager.connect()
    db_manager.create_table() # This will now drop and recreate the table

    # Create a test DataFrame with NLP and opportunity fields
    test_data = {
        'id': ['test_opp_1', 'test_opp_2', 'test_opp_3'],
        'title': ['Δοκιμαστικό Νέο 1', 'Δοκιμαστικό Νέο 2', 'Δοκιμαστικό Νέο 3 με αλλαγή'],
        'url': ['http://example.com/news1', 'http://example.com/news2', 'http://example.com/news3'],
        'date': [pd.to_datetime('2024-01-01').date(), pd.to_datetime('2024-01-02').date(), pd.to_datetime('2024-01-03').date()],
        'source': ['TestSource', 'Test2', 'Test3'],
        'keywords': ['δοκιμή', 'πρόγραμμα', 'αλλαγή, ενημέρωση'],
        'entities': ["[]", "[('Test2', 'ORG')]", "[('Test3', 'LOC')]"],
        'main_topic': ['Γενικά', 'Πρόγραμμα', 'Ενημέρωση'],
        'full_text': [None, None, None],
        'sentiment': [None, None, None],
        'opportunity_score': [10.0, 5.0, 15.0], # Example scores
        'opportunity_type': ['Γενική Φορολογική Είδηση', 'Αναπτυξιακά / Κίνητρα / Επιδότηση', 'Αλλαγή Φορολογικής Νομοθεσίας']
    }
    test_df = pd.DataFrame(test_data)

    print("\nInserting/updating test data (first batch)...")
    db_manager.insert_opportunities(test_df.iloc[[0, 1]])

    print("\nAttempting to insert/update more data (including duplicates and new entry)...")
    # This will update test_opp_1 and insert test_opp_3
    test_update_df = pd.DataFrame({
        'id': ['test_opp_1', 'test_opp_3', 'test_opp_4'],
        'title': ['Δοκιμαστικό Νέο 1 (Updated)', 'Δοκιμαστικό Νέο 3 (Updated)', 'Δοκιμαστικό Νέο 4 (New)'],
        'url': ['http://example.com/news1', 'http://example.com/news3', 'http://example.com/news4_new'],
        'date': [pd.to_datetime('2024-01-01').date(), pd.to_datetime('2024-01-03').date(), pd.to_datetime('2024-01-04').date()],
        'source': ['TestSource', 'Test3', 'Test4'],
        'keywords': ['δοκιμή, ενημέρωση', 'αλλαγή, ενημέρωση, νέο', 'προσθήκη'],
        'entities': ["[]", "[('Test3', 'LOC')]", "[]"],
        'main_topic': ['Γενικά', 'Ενημέρωση', 'Νέο'],
        'full_text': [None, None, None],
        'sentiment': [None, None, None],
        'opportunity_score': [12.0, 18.0, 7.0],
        'opportunity_type': ['Αλλαγή Φορολογικής Νομοθεσίας', 'Αλλαγή Φορολογικής Νομοθεσίας', 'Γενική Φορολογική Είδηση']
    })
    db_manager.insert_opportunities(test_update_df)

    print("\nRetrieving all data:")
    all_data = db_manager.fetch_all_opportunities()
    print(all_data[['title', 'date', 'source', 'opportunity_score', 'opportunity_type', 'keywords', 'main_topic']])

    db_manager.close()
    print("\nDBManager test completed.")