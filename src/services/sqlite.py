import os
import sys
import sqlite3
import logging
from typing import Optional, List, Tuple, Any

# Setup logging to a file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log',        # Logs will be saved to 'app.log'
    filemode='a'               # Append mode (use 'w' to overwrite on each run)
)

logger = logging.getLogger(__name__)

# Set project root path
cwd = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(cwd)

from src.models.config import Config

cfg = Config.from_yaml(filepath=os.path.join(
                cwd, 'src', 'config.yaml'
            ))


class TariffDB:
    """Database handler for shipping tariff data."""

    def __init__(self, config: Config):
        """
        Initialize the database handler.
        
        Args:
            config: Configuration object containing database settings
        """
        self.db_path = os.path.join(cwd, config.sqlite.name)
        logger.info("Database initialized at: %s", self.db_path)

    def _get_connection(self) -> sqlite3.Connection:
        """
        Create and return a database connection.
        
        Returns:
            SQLite connection object
        """
        return sqlite3.connect(database=self.db_path)

    def create_db(self) -> bool:
        """
        Create the shipping_tariffs table if it doesn't exist.
        
        Returns:
            bool: True if successful, False if an error occurred
        """
        query = """
        CREATE TABLE IF NOT EXISTS shipping_tariffs (
            doc_id VARCHAR(255) PRIMARY KEY,
            Type VARCHAR(255),
            Country VARCHAR(255),
            "Liner Name" VARCHAR(255),
            Port VARCHAR(255),
            "Equipment Type" VARCHAR(255),
            Currency VARCHAR(10),
            "Free days" INTEGER NULL,
            "Bucket 1" VARCHAR(255) NULL,
            "Bucket 2" VARCHAR(255) NULL,
            "Bucket 3" VARCHAR(255) NULL
        );
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            conn.commit()
            logger.info("Database table created successfully")
            return True
        except Exception as e:
            logger.error("Error creating database: %s", str(e))
            return False
        finally:
            if conn:
                conn.close()

    def fetch_records(self) -> Optional[List[Tuple]]:
        """
        Fetch all records from the shipping_tariffs table.
        
        Returns:
            List of record tuples or None if an error occurred
        """
        query = """
        SELECT *
        FROM shipping_tariffs;
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            records = cursor.fetchall()
            logger.info("Fetched %s records from database", len(records))
            return records
        except Exception as e:
            logger.error("Error fetching records: %s", str(e))
            return None
        finally:
            if conn:
                conn.close()

    def insert_record(self, data: tuple) -> bool:
        """
        Insert a new tariff record into the database.
        
        Args:
            data: Tuple containing (Country, Type, Liner Name, Port, Equipment Type, 
                  Currency, Free days, Bucket 1, Bucket 2, Bucket 3, doc_id)
        
        Returns:
            bool: True if successful, False if an error occurred
        """
        query = """
        INSERT OR REPLACE INTO shipping_tariffs (
            Country,
            Type,
            "Liner Name",
            Port,
            "Equipment Type",
            Currency,
            "Free days",
            "Bucket 1",
            "Bucket 2",
            "Bucket 3",
            doc_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, data)
            conn.commit()
            logger.info("Record inserted successfully: %s", data[-1])  # Log doc_id
            return True
        except Exception as e:
            logger.error("Error inserting record: %s, Data: %s", str(e), data )
            return False
        finally:
            if conn:
                conn.close()

    def query_by_country(self, country: str) -> Optional[List[Tuple]]:
        """
        Query records for a specific country.
        
        Args:
            country: Country name to search for
            
        Returns:
            List of matching records or None if an error occurred
        """
        query = """
        SELECT *
        FROM shipping_tariffs
        WHERE Country = ?;
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (country,))
            records = cursor.fetchall()
            logger.info("Found %s records for country: %s", len(records), country)
            return records
        except Exception as e:
            logger.error("Error querying by country: %s", str(e))
            return None
        finally:
            if conn:
                conn.close()
