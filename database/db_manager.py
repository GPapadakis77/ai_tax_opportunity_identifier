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
            # print(f"Successfully connected to the database: {self.db_path}")
        except sqlite3.Error as e:
            print(f"Error connecting to the database: {e}")
            self.conn = None

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            # print("Database connection closed.")

    def create_table(self):
        """
        Creates the 'opportunities' table if it doesn't exist.
        The URL is the primary key, ensuring no duplicate articles.
        """
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS opportunities (
                url TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                date DATE,
                source TEXT,
                full_text TEXT,
                keywords TEXT,
                entities TEXT,
                main_topic TEXT,
                opportunity_score REAL,
                opportunity_type TEXT,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
        # print("The 'opportunities' table is ready.")

    def insert_opportunities(self, df):
        """
        Inserts or replaces opportunities from a DataFrame into the table
        using the efficient pandas `to_sql` method.
        """
        if df.empty or 'url' not in df.columns:
            print("No data or 'url' column found to insert.")
            return

        if not self.conn:
            self.connect()

        # Prepare DataFrame by ensuring all table columns exist
        table_columns = [
            'url', 'title', 'date', 'source', 'full_text', 'keywords', 
            'entities', 'main_topic', 'opportunity_score', 'opportunity_type'
        ]
        
        df_to_insert = df.copy()
        for col in table_columns:
            if col not in df_to_insert.columns:
                df_to_insert[col] = None
        
        # Keep only the columns that exist in the table to avoid errors
        df_to_insert = df_to_insert[table_columns]

        try:
            # Use pandas to_sql which is highly optimized for this task
            df_to_insert.to_sql(
                'opportunities', 
                self.conn, 
                if_exists='append', 
                index=False,
                # Use a custom method to perform 'INSERT OR REPLACE'
                # This is a powerful feature for handling updates
                method=lambda table, conn, keys, data_iter: conn.executemany(
                    f"INSERT OR REPLACE INTO {table.name} ({', '.join(keys)}) VALUES ({', '.join(['?'] * len(keys))})",
                    data_iter
                )
            )
            print(f"Insertion/update of {len(df)} opportunities completed in the database.")
        except sqlite3.Error as e:
            print(f"Error during bulk insert/update: {e}")

    def fetch_all_opportunities(self):
        """Retrieves all opportunities from the database into a DataFrame."""
        if not self.conn:
            self.connect()
        
        try:
            df = pd.read_sql_query("SELECT * FROM opportunities ORDER BY date DESC", self.conn)
            # Ensure correct data types after fetching
            df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
            df['opportunity_score'] = pd.to_numeric(df['opportunity_score'], errors='coerce')
            return df
        except Exception as e:
            print(f"Could not fetch data from database: {e}")
            return pd.DataFrame()

# Test function for the module
if __name__ == "__main__":
    print("Running db_manager.py directly (for testing).")
    db_manager = DBManager(db_name="test_opportunities.db")
    db_manager.connect()
    
    # Clean slate for testing
    cursor = db_manager.conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS opportunities;")
    db_manager.conn.commit()
    
    db_manager.create_table()

    # Create initial test data
    test_data = {
        'url': ['http://example.com/news1', 'http://example.com/news2'],
        'title': ['Test News 1', 'Test News 2'],
        'date': [pd.to_datetime('2024-01-01').date(), pd.to_datetime('2024-01-02').date()],
        'source': ['TestSource', 'Test2'],
        'opportunity_score': [5.0, 8.0]
    }
    test_df = pd.DataFrame(test_data)
    
    print("\nInserting initial data...")
    db_manager.insert_opportunities(test_df)
    
    # Create update data (update news1, add news3)
    update_data = {
        'url': ['http://example.com/news1', 'http://example.com/news3'],
        'title': ['Test News 1 (Updated)', 'Test News 3 (New)'],
        'date': [pd.to_datetime('2024-01-01').date(), pd.to_datetime('2024-01-03').date()],
        'source': ['TestSource', 'Test3'],
        'opportunity_score': [7.5, 9.0]
    }
    update_df = pd.DataFrame(update_data)
    
    print("\nInserting updated/new data...")
    db_manager.insert_opportunities(update_df)
    
    print("\nRetrieving all data to verify:")
    all_data = db_manager.fetch_all_opportunities()
    print(all_data[['title', 'date', 'source', 'opportunity_score']])

    db_manager.close()