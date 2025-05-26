import os
from dotenv import load_dotenv
import sys

# Import SQLAlchemy components
try:
    from sqlalchemy import create_engine, text
    sqlalchemy_available = True
except ImportError:
    sqlalchemy_available = False

def test_database_connection():
    # Load environment variables from .env file
    load_dotenv("app/.env")
    
    # Get database connection parameters
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_name = os.getenv('DB_NAME')
    db_port = os.getenv('DB_PORT', '5432')  # Default PostgreSQL port if not specified
    
    # Print connection parameters (without password)
    print(f"Database connection parameters:")
    print(f"  User: {db_user}")
    print(f"  Host: {db_host}")
    print(f"  Port: {db_port}")
    print(f"  Database: {db_name}")
    
    # Create database URL
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    print(f"\nConnection string (with password hidden):")
    hidden_url = f"postgresql://{db_user}:****@{db_host}:{db_port}/{db_name}"
    print(f"  {hidden_url}")
    
    if not sqlalchemy_available:
        print("\nSQLAlchemy is not available. Cannot test database connection.")
        print("Please install SQLAlchemy and psycopg2-binary to test the connection.")
        return
    
    print("\nAttempting to connect to the database...")
    try:
        # Create engine
        engine = create_engine(database_url)
        
        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("\n✅ Connection successful!")
            print("Database is reachable and credentials are correct.")
            
            # Get PostgreSQL version
            version_result = connection.execute(text("SELECT version()"))
            version = version_result.scalar()
            print(f"\nPostgreSQL Version: {version}")
            
            # Check if the backend app tables exist
            try:
                tables_result = connection.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'"))
                tables = [row[0] for row in tables_result]
                
                if tables:
                    print("\nExisting tables in the database:")
                    for table in tables:
                        print(f"  - {table}")
                else:
                    print("\nNo tables found in the database.")
                    print("Your backend application may need to create the tables.")
            except Exception as e:
                print(f"\nCould not query tables: {str(e)}")
    except Exception as e:
        print("\n❌ Connection failed!")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_database_connection()
