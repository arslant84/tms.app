# Custom migration to recreate role and permission tables with UUID primary keys

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_populate_default_settings'),
    ]

    operations = [
        # Drop existing tables and recreate with UUIDs
        migrations.RunSQL(
            sql=[
                # Drop existing tables
                "DROP TABLE IF EXISTS accounts_rolepermission CASCADE;",
                "DROP TABLE IF EXISTS accounts_role CASCADE;",
                "DROP TABLE IF EXISTS accounts_permission CASCADE;",

                # Create Permission table with UUID
                """
                CREATE TABLE accounts_permission (
                    id UUID PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """,

                # Create Role table with UUID
                """
                CREATE TABLE accounts_role (
                    id UUID PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """,

                # Create RolePermission join table
                """
                CREATE TABLE accounts_rolepermission (
                    id SERIAL PRIMARY KEY,
                    role_id UUID NOT NULL REFERENCES accounts_role(id) ON DELETE CASCADE,
                    permission_id UUID NOT NULL REFERENCES accounts_permission(id) ON DELETE CASCADE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(role_id, permission_id)
                );
                """,

                # Convert accounts_user.role_id to UUID
                """
                ALTER TABLE accounts_user
                ALTER COLUMN role_id DROP DEFAULT,
                ALTER COLUMN role_id TYPE UUID USING NULL;
                """,

                # Re-add foreign key constraint to accounts_user
                """
                ALTER TABLE accounts_user
                ADD CONSTRAINT accounts_user_role_id_fk
                FOREIGN KEY (role_id) REFERENCES accounts_role(id)
                ON DELETE SET NULL;
                """,
            ],
            reverse_sql=[
                "DROP TABLE IF EXISTS accounts_rolepermission CASCADE;",
                "DROP TABLE IF EXISTS accounts_role CASCADE;",
                "DROP TABLE IF EXISTS accounts_permission CASCADE;",
            ]
        ),
    ]
