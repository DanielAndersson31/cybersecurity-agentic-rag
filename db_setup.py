"""
Database setup script for the cybersecurity knowledge base.
This script initializes and populates the vector database with cybersecurity documents.
"""

from database.vector_store import DatabaseManager

def setup_and_test_database(persist_directory: str = "./chroma_db"):
    """
    Main function to setup and test the cybersecurity knowledge database.
    
    Args:
        persist_directory (str): Directory to store the Chroma database
        
    Returns:
        DatabaseManager: Initialized database manager instance
    """
    print("=== Cybersecurity Knowledge Database Setup ===")
    
    # Initialize the database manager
    db_manager = DatabaseManager(persist_directory)
    
    # Setup and populate the database
    if db_manager.setup_database():
        print("\n=== Database Setup Complete ===")
        
        # Test the search functionality
        db_manager.test_searches()
        
        print("\n=== Setup and Testing Complete ===")
        return db_manager
    else:
        print("\n=== Database Setup Failed ===")
        return None

def main():
    """Main execution function."""
    db_manager = setup_and_test_database("./chroma_db")
    
    if db_manager:
        print("\nDatabase is ready for use!")
        print("You can now import DatabaseManager from database.vector_store in your application.")
    else:
        print("\nDatabase setup failed. Please check the error messages above.")

if __name__ == "__main__":
    main() 