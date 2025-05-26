"""
Script to update the database schema for the Travel Request Management System.
This adds the new columns to the users table and travel_requests table.
"""
import os
from sqlalchemy import create_engine, text
from app.database import DATABASE_URL

def update_schema():
    """Update the database schema to add new columns."""
    print("Connecting to database...")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as connection:
        # Begin a transaction
        with connection.begin():
            print("Adding new columns to users table...")
            
            # Check if columns already exist before adding them
            # Add hashed_password column
            connection.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'hashed_password'
                    ) THEN
                        ALTER TABLE users ADD COLUMN hashed_password VARCHAR;
                    END IF;
                END
                $$;
            """))
            
            # Add is_admin column
            connection.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'is_admin'
                    ) THEN
                        ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;
                    END IF;
                END
                $$;
            """))
            
            # Add is_active column
            connection.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'is_active'
                    ) THEN
                        ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
                    END IF;
                END
                $$;
            """))
            
            # Add role column
            connection.execute(text("""
                DO $$
                BEGIN
                    -- First create the enum type if it doesn't exist
                    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole') THEN
                        CREATE TYPE userrole AS ENUM ('employee', 'focal', 'hod', 'ticketing_clerk', 'external');
                    END IF;
                    
                    -- Then add the column if it doesn't exist
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'role'
                    ) THEN
                        ALTER TABLE users ADD COLUMN role userrole DEFAULT 'employee';
                    END IF;
                END
                $$;
            """))
            
            # Add department column if it doesn't exist
            connection.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'department'
                    ) THEN
                        ALTER TABLE users ADD COLUMN department VARCHAR DEFAULT 'General';
                    END IF;
                END
                $$;
            """))
            
            print("Adding new columns to travel_requests table...")
            
            # Add new columns to travel_requests table
            # Add submission_date column
            connection.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'travel_requests' AND column_name = 'submission_date'
                    ) THEN
                        ALTER TABLE travel_requests ADD COLUMN submission_date TIMESTAMP;
                    END IF;
                END
                $$;
            """))
            
            # Add review_date column
            connection.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'travel_requests' AND column_name = 'review_date'
                    ) THEN
                        ALTER TABLE travel_requests ADD COLUMN review_date TIMESTAMP;
                    END IF;
                END
                $$;
            """))
            
            # Add approval_date column
            connection.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'travel_requests' AND column_name = 'approval_date'
                    ) THEN
                        ALTER TABLE travel_requests ADD COLUMN approval_date TIMESTAMP;
                    END IF;
                END
                $$;
            """))
            
            # Add processing_date column
            connection.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'travel_requests' AND column_name = 'processing_date'
                    ) THEN
                        ALTER TABLE travel_requests ADD COLUMN processing_date TIMESTAMP;
                    END IF;
                END
                $$;
            """))
            
            # Add rejection_date column
            connection.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'travel_requests' AND column_name = 'rejection_date'
                    ) THEN
                        ALTER TABLE travel_requests ADD COLUMN rejection_date TIMESTAMP;
                    END IF;
                END
                $$;
            """))
            
            # Add rejection_reason column
            connection.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'travel_requests' AND column_name = 'rejection_reason'
                    ) THEN
                        ALTER TABLE travel_requests ADD COLUMN rejection_reason TEXT;
                    END IF;
                END
                $$;
            """))
            
            # Add authority_letter_no column
            connection.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'travel_requests' AND column_name = 'authority_letter_no'
                    ) THEN
                        ALTER TABLE travel_requests ADD COLUMN authority_letter_no VARCHAR;
                    END IF;
                END
                $$;
            """))
            
            # Add organization column
            connection.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'travel_requests' AND column_name = 'organization'
                    ) THEN
                        ALTER TABLE travel_requests ADD COLUMN organization VARCHAR;
                    END IF;
                END
                $$;
            """))
            
            # Add hlp_number column
            connection.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'travel_requests' AND column_name = 'hlp_number'
                    ) THEN
                        ALTER TABLE travel_requests ADD COLUMN hlp_number VARCHAR;
                    END IF;
                END
                $$;
            """))
            
            # Add travel_start_date column
            connection.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'travel_requests' AND column_name = 'travel_start_date'
                    ) THEN
                        ALTER TABLE travel_requests ADD COLUMN travel_start_date TIMESTAMP;
                    END IF;
                END
                $$;
            """))
            
            # Add travel_end_date column
            connection.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'travel_requests' AND column_name = 'travel_end_date'
                    ) THEN
                        ALTER TABLE travel_requests ADD COLUMN travel_end_date TIMESTAMP;
                    END IF;
                END
                $$;
            """))
            
    print("Database schema updated successfully!")

if __name__ == "__main__":
    update_schema()
