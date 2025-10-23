#!/usr/bin/env python
"""Migrate notification templates and event types from syntra to tms database"""
import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

# Database connection details
SYNTRA_DB = {
    'dbname': 'syntra',
    'user': 'postgres',
    'password': '221202',
    'host': 'localhost',
    'port': '5432'
}

TMS_DB = {
    'dbname': 'tms',
    'user': 'postgres',
    'password': '221202',
    'host': 'localhost',
    'port': '5432'
}

def migrate_event_types():
    """Migrate notification event types from syntra to tms"""
    print("=== MIGRATING NOTIFICATION EVENT TYPES ===\n")

    # Connect to both databases
    syntra_conn = psycopg2.connect(**SYNTRA_DB)
    tms_conn = psycopg2.connect(**TMS_DB)

    syntra_cur = syntra_conn.cursor(cursor_factory=RealDictCursor)
    tms_cur = tms_conn.cursor()

    try:
        # Fetch all event types from syntra
        syntra_cur.execute("""
            SELECT id, name, description, category, module, is_active, created_at, updated_at
            FROM notification_event_types
            ORDER BY module, category, name
        """)

        event_types = syntra_cur.fetchall()
        print(f"✓ Found {len(event_types)} event types in syntra database\n")

        # Clear existing event types in tms (if any)
        tms_cur.execute("TRUNCATE TABLE notification_event_types CASCADE;")
        print("✓ Cleared existing event types in tms database\n")

        # Insert event types into tms
        insert_count = 0
        for et in event_types:
            tms_cur.execute("""
                INSERT INTO notification_event_types
                (id, name, description, category, module, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                et['id'],
                et['name'],
                et['description'],
                et['category'],
                et['module'],
                et['is_active'],
                et['created_at'],
                et['updated_at']
            ))
            insert_count += 1
            print(f"  ✓ {et['name']} ({et['module']}/{et['category']})")

        tms_conn.commit()
        print(f"\n✅ Successfully migrated {insert_count} event types\n")

        return event_types

    except Exception as e:
        print(f"❌ Error migrating event types: {e}")
        tms_conn.rollback()
        raise
    finally:
        syntra_cur.close()
        tms_cur.close()
        syntra_conn.close()
        tms_conn.close()


def migrate_templates():
    """Migrate notification templates from syntra to tms"""
    print("=== MIGRATING NOTIFICATION TEMPLATES ===\n")

    # Connect to both databases
    syntra_conn = psycopg2.connect(**SYNTRA_DB)
    tms_conn = psycopg2.connect(**TMS_DB)

    syntra_cur = syntra_conn.cursor(cursor_factory=RealDictCursor)
    tms_cur = tms_conn.cursor()

    try:
        # Fetch all templates from syntra
        syntra_cur.execute("""
            SELECT id, name, subject, body, description, event_type_id,
                   notification_type, is_active, variables_available,
                   recipient_type, created_at, updated_at
            FROM notification_templates
            ORDER BY name
        """)

        templates = syntra_cur.fetchall()
        print(f"✓ Found {len(templates)} templates in syntra database\n")

        # Clear existing templates in tms (if any)
        tms_cur.execute("TRUNCATE TABLE notification_templates CASCADE;")
        print("✓ Cleared existing templates in tms database\n")

        # Insert templates into tms
        insert_count = 0
        active_count = 0

        for template in templates:
            tms_cur.execute("""
                INSERT INTO notification_templates
                (id, name, subject, body, description, event_type_id,
                 notification_type, is_active, variables_available,
                 recipient_type, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                template['id'],
                template['name'],
                template['subject'],
                template['body'],
                template['description'],
                template['event_type_id'],
                template['notification_type'],
                template['is_active'],
                template['variables_available'],
                template['recipient_type'],
                template['created_at'],
                template['updated_at']
            ))
            insert_count += 1

            status_icon = "✓" if template['is_active'] else "○"
            print(f"  {status_icon} {template['name']} ({template['notification_type']}/{template['recipient_type']})")

            if template['is_active']:
                active_count += 1

        tms_conn.commit()
        print(f"\n✅ Successfully migrated {insert_count} templates ({active_count} active)\n")

        return templates

    except Exception as e:
        print(f"❌ Error migrating templates: {e}")
        tms_conn.rollback()
        raise
    finally:
        syntra_cur.close()
        tms_cur.close()
        syntra_conn.close()
        tms_conn.close()


def verify_migration():
    """Verify the migration was successful"""
    print("=== VERIFYING MIGRATION ===\n")

    tms_conn = psycopg2.connect(**TMS_DB)
    tms_cur = tms_conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Count event types
        tms_cur.execute("SELECT COUNT(*) as count FROM notification_event_types;")
        event_count = tms_cur.fetchone()['count']
        print(f"✓ Event Types: {event_count}")

        # Count templates
        tms_cur.execute("SELECT COUNT(*) as count FROM notification_templates;")
        template_count = tms_cur.fetchone()['count']
        print(f"✓ Templates: {template_count}")

        # Count active templates
        tms_cur.execute("SELECT COUNT(*) as count FROM notification_templates WHERE is_active = true;")
        active_count = tms_cur.fetchone()['count']
        print(f"✓ Active Templates: {active_count}")

        # Group by module
        print("\n✓ Event Types by Module:")
        tms_cur.execute("""
            SELECT module, COUNT(*) as count
            FROM notification_event_types
            GROUP BY module
            ORDER BY module
        """)
        for row in tms_cur.fetchall():
            print(f"  - {row['module']}: {row['count']}")

        # Group templates by type
        print("\n✓ Templates by Type:")
        tms_cur.execute("""
            SELECT notification_type, COUNT(*) as count
            FROM notification_templates
            GROUP BY notification_type
            ORDER BY notification_type
        """)
        for row in tms_cur.fetchall():
            print(f"  - {row['notification_type']}: {row['count']}")

        # Group templates by recipient
        print("\n✓ Templates by Recipient:")
        tms_cur.execute("""
            SELECT recipient_type, COUNT(*) as count
            FROM notification_templates
            GROUP BY recipient_type
            ORDER BY recipient_type
        """)
        for row in tms_cur.fetchall():
            print(f"  - {row['recipient_type']}: {row['count']}")

        print("\n✅ Migration verified successfully!")

    finally:
        tms_cur.close()
        tms_conn.close()


if __name__ == '__main__':
    try:
        print("\n" + "="*60)
        print("NOTIFICATION TEMPLATES MIGRATION")
        print("Source: syntra database")
        print("Target: tms database")
        print("="*60 + "\n")

        # Step 1: Migrate event types
        event_types = migrate_event_types()

        # Step 2: Migrate templates
        templates = migrate_templates()

        # Step 3: Verify
        verify_migration()

        print("\n" + "="*60)
        print("✅ MIGRATION COMPLETE!")
        print("="*60 + "\n")

        print("Summary:")
        print(f"  - Event Types: {len(event_types)}")
        print(f"  - Templates: {len(templates)}")
        print(f"  - Active Templates: {sum(1 for t in templates if t['is_active'])}")
        print("\nYou can now:")
        print("  1. Access notification templates at /admin/settings/notifications")
        print("  2. Create new custom templates")
        print("  3. Edit existing templates")
        print("  4. Assign templates to event types")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)
