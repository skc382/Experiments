import logging
from neo4j import GraphDatabase
import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Neo4jClearDatabase:
    def __init__(self, uri, username, password):
        """
        Initialize Neo4j driver.
        Args:
            uri (str): Neo4j Aura URI (e.g., neo4j+s://<instance>.databases.neo4j.io)
            username (str): Neo4j username (e.g., neo4j)
            password (str): Neo4j password
        """
        try:
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            logger.info("Neo4j driver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j driver: {str(e)}")
            raise

    def close(self):
        """Close the Neo4j driver."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j driver closed")

    def clear_database(self):
        """Delete all nodes, relationships, and properties in the database."""
        query = "MATCH (n) DETACH DELETE n"
        try:
            with self.driver.session() as session:
                session.execute_write(self._execute_clear, query)
                logger.info("Database cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing database: {str(e)}")
            raise

    @staticmethod
    def _execute_clear(tx, query):
        """
        Execute the clear database query within a transaction.
        Args:
            tx: Neo4j transaction
            query (str): Cypher query to clear the database
        """
        tx.run(query)

def main():
    # Environment variables
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")

    # Initialize and clear database
    db_clearer = Neo4jClearDatabase(uri, username, password)
    try:
        db_clearer.clear_database()
    finally:
        db_clearer.close()

if __name__ == "__main__":
    main()