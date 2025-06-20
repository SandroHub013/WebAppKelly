import sqlite3
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()

    def connect(self):
        """Connect to the SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            logger.info("Connected to database successfully")
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database: {e}")
            raise

    def create_tables(self):
        """Create necessary tables if they don't exist."""
        try:
            # Create events table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    event_name TEXT NOT NULL,
                    odds REAL NOT NULL,
                    probability REAL NOT NULL,
                    bankroll REAL NOT NULL,
                    kelly_percentage REAL NOT NULL,
                    fraction_label TEXT NOT NULL,
                    bet_amount REAL NOT NULL,
                    outcome INTEGER,
                    return_value REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create bankroll_history table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS bankroll_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    bankroll REAL NOT NULL,
                    event_id INTEGER,
                    description TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events (event_id)
                )
            ''')

            self.conn.commit()
            logger.info("Tables created successfully")
        except sqlite3.Error as e:
            logger.error(f"Error creating tables: {e}")
            raise

    def insert_event(self, user_id, chat_id, odds, probability, bankroll, kelly_percentage, fraction_label, bet_amount, event_name):
        """Insert a new event into the database."""
        try:
            self.cursor.execute('''
                INSERT INTO events (user_id, chat_id, odds, probability, bankroll, kelly_percentage, fraction_label, bet_amount, event_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, chat_id, odds, probability, bankroll, kelly_percentage, fraction_label, bet_amount, event_name))
            self.conn.commit()
            logger.info(f"Event inserted successfully for user {user_id}")
        except sqlite3.Error as e:
            logger.error(f"Error inserting event: {e}")
            raise

    def update_event_outcome(self, event_id, outcome, return_value):
        """Update the outcome of an event."""
        try:
            self.cursor.execute('''
                UPDATE events
                SET outcome = ?, return_value = ?
                WHERE event_id = ?
            ''', (outcome, return_value, event_id))
            self.conn.commit()
            logger.info(f"Event {event_id} outcome updated successfully")
        except sqlite3.Error as e:
            logger.error(f"Error updating event outcome: {e}")
            raise

    def get_events(self, user_id, chat_id):
        """Get all events for a user in a chat."""
        try:
            self.cursor.execute('''
                SELECT * FROM events
                WHERE user_id = ? AND chat_id = ?
                ORDER BY timestamp DESC
            ''', (user_id, chat_id))
            columns = [description[0] for description in self.cursor.description]
            events = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            return events
        except sqlite3.Error as e:
            logger.error(f"Error getting events: {e}")
            raise

    def get_event_odds(self, event_id):
        """Get the odds for a specific event."""
        try:
            self.cursor.execute('''
                SELECT odds FROM events
                WHERE event_id = ?
            ''', (event_id,))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            logger.error(f"Error getting event odds: {e}")
            raise

    def update_bankroll(self, user_id, chat_id, new_bankroll, event_id=None, description=None):
        """Update the bankroll for a user in a chat."""
        try:
            self.cursor.execute('''
                INSERT INTO bankroll_history (user_id, chat_id, bankroll, event_id, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, chat_id, new_bankroll, event_id, description))
            self.conn.commit()
            logger.info(f"Bankroll updated successfully for user {user_id}")
        except sqlite3.Error as e:
            logger.error(f"Error updating bankroll: {e}")
            raise

    def get_current_bankroll(self, user_id, chat_id):
        """Get the current bankroll for a user in a chat."""
        try:
            self.cursor.execute('''
                SELECT bankroll FROM bankroll_history
                WHERE user_id = ? AND chat_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (user_id, chat_id))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            logger.error(f"Error getting current bankroll: {e}")
            raise

    def get_initial_bankroll(self, user_id, chat_id):
        """Get the initial bankroll for a user in a chat."""
        try:
            self.cursor.execute('''
                SELECT bankroll FROM bankroll_history
                WHERE user_id = ? AND chat_id = ?
                ORDER BY timestamp ASC
                LIMIT 1
            ''', (user_id, chat_id))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            logger.error(f"Error getting initial bankroll: {e}")
            raise

    def update_initial_bankroll(self, user_id, chat_id, new_bankroll):
        """Update the initial bankroll for a user in a chat."""
        try:
            # First, check if there's any existing bankroll history
            self.cursor.execute('''
                SELECT COUNT(*) FROM bankroll_history
                WHERE user_id = ? AND chat_id = ?
            ''', (user_id, chat_id))
            count = self.cursor.fetchone()[0]

            if count == 0:
                # If no history exists, insert the initial bankroll
                self.cursor.execute('''
                    INSERT INTO bankroll_history (user_id, chat_id, bankroll, description)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, chat_id, new_bankroll, "Bankroll iniziale"))
            else:
                # If history exists, update the most recent entry
                self.cursor.execute('''
                    UPDATE bankroll_history
                    SET bankroll = ?, description = ?
                    WHERE id = (
                        SELECT id FROM bankroll_history
                        WHERE user_id = ? AND chat_id = ?
                        ORDER BY timestamp DESC
                        LIMIT 1
                    )
                ''', (new_bankroll, "Bankroll iniziale aggiornato", user_id, chat_id))

            self.conn.commit()
            logger.info(f"Initial bankroll updated successfully for user {user_id}")
        except sqlite3.Error as e:
            logger.error(f"Error updating initial bankroll: {e}")
            raise

    def delete_event(self, event_id):
        """Delete an event from the database."""
        try:
            # First, check if the event exists
            self.cursor.execute('''
                SELECT event_id FROM events
                WHERE event_id = ?
            ''', (event_id,))
            if not self.cursor.fetchone():
                logger.error(f"Event {event_id} not found")
                return False

            # Delete the event
            self.cursor.execute('''
                DELETE FROM events
                WHERE event_id = ?
            ''', (event_id,))
            
            self.conn.commit()
            logger.info(f"Event {event_id} deleted successfully")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error deleting event: {e}")
            return False

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed") 