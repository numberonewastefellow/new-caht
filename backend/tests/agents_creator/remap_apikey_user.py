#!/usr/bin/env python3
"""
Remap an API key's synthetic user to a real user account.

After running this, all operations performed with the API key will be
attributed to the real user (e.g. v@v.com) instead of the synthetic
API_KEY__xxx@onyxapikey.ai user.

Usage:
    python remap_apikey_user.py                     # defaults to v@v.com
    python remap_apikey_user.py --email admin@x.com
    python remap_apikey_user.py --email v@v.com --db-host 127.0.0.1
    python remap_apikey_user.py --dry-run            # preview without changes

Requires: psycopg2  (pip install psycopg2-binary)
"""

import argparse
import hashlib
import os
import sys
from pathlib import Path

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: psycopg2 is required.  Install with:  pip install psycopg2-binary")
    sys.exit(1)

ROOT_DIR = Path(__file__).parent
APIKEY_FILE = ROOT_DIR / "apikey.txt"

# API key prefix used by the system
API_KEY_PREFIX = "on_"


def load_api_key() -> str:
    """Read the API key from apikey.txt."""
    if not APIKEY_FILE.exists():
        print(f"ERROR: {APIKEY_FILE} not found")
        sys.exit(1)
    for line in APIKEY_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    print("ERROR: apikey.txt is empty or contains only comments")
    sys.exit(1)


def hash_api_key(api_key: str) -> str:
    """Hash the API key the same way the backend does (SHA-256)."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def get_db_connection(args):
    """Connect to the PostgreSQL database."""
    conn = psycopg2.connect(
        host=args.db_host,
        port=args.db_port,
        dbname=args.db_name,
        user=args.db_user,
        password=args.db_password,
    )
    return conn


def main():
    parser = argparse.ArgumentParser(
        description="Remap an API key to a real user account"
    )
    parser.add_argument(
        "--email",
        default="v@v.com",
        help="Target user email to map the API key to (default: v@v.com)",
    )
    parser.add_argument(
        "--db-host",
        default=os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        help="PostgreSQL host (default: $POSTGRES_HOST or 127.0.0.1)",
    )
    parser.add_argument(
        "--db-port",
        default=os.environ.get("POSTGRES_PORT", "5432"),
        help="PostgreSQL port (default: $POSTGRES_PORT or 5432)",
    )
    parser.add_argument(
        "--db-name",
        default=os.environ.get("POSTGRES_DB", "postgres"),
        help="PostgreSQL database (default: $POSTGRES_DB or postgres)",
    )
    parser.add_argument(
        "--db-user",
        default=os.environ.get("POSTGRES_USER", "postgres"),
        help="PostgreSQL user (default: $POSTGRES_USER or postgres)",
    )
    parser.add_argument(
        "--db-password",
        default=os.environ.get("POSTGRES_PASSWORD", "password"),
        help="PostgreSQL password (default: $POSTGRES_PASSWORD or password)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying the database",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete the orphaned synthetic user after remapping",
    )
    args = parser.parse_args()

    # ── Step 1: Read and hash the API key ────────────────────────────────
    api_key = load_api_key()
    hashed = hash_api_key(api_key)
    display_key = f"{api_key[:8]}...{api_key[-4:]}"
    print(f"API key:     {display_key}")
    print(f"SHA-256:     {hashed[:16]}...")

    # ── Step 2: Connect to the database ──────────────────────────────────
    try:
        conn = get_db_connection(args)
    except Exception as e:
        print(f"\nERROR: Cannot connect to PostgreSQL: {e}")
        print("  Make sure the database is running and connection parameters are correct.")
        sys.exit(1)

    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # ── Step 3: Find the API key record ──────────────────────────────
        cur.execute(
            "SELECT id, user_id, owner_id, name, api_key_display "
            "FROM api_key WHERE hashed_api_key = %s",
            (hashed,),
        )
        api_key_row = cur.fetchone()

        if not api_key_row:
            print("\nERROR: API key not found in the database.")
            print("  Make sure the key in apikey.txt matches a key created in VirtualAI.")
            sys.exit(1)

        print(f"\nAPI key record found:")
        print(f"  ID:          {api_key_row['id']}")
        print(f"  Name:        {api_key_row['name']}")
        print(f"  Display:     {api_key_row['api_key_display']}")
        print(f"  user_id:     {api_key_row['user_id']}")
        print(f"  owner_id:    {api_key_row['owner_id']}")

        old_user_id = api_key_row["user_id"]

        # ── Step 4: Look up the current synthetic user ───────────────────
        cur.execute(
            "SELECT id, email, role FROM \"user\" WHERE id = %s",
            (old_user_id,),
        )
        synthetic_user = cur.fetchone()
        if synthetic_user:
            print(f"\nCurrent synthetic user:")
            print(f"  Email: {synthetic_user['email']}")
            print(f"  Role:  {synthetic_user['role']}")

        # ── Step 5: Find the target real user ────────────────────────────
        cur.execute(
            "SELECT id, email, role FROM \"user\" WHERE email = %s",
            (args.email,),
        )
        target_user = cur.fetchone()

        if not target_user:
            print(f"\nERROR: User '{args.email}' not found in the database.")
            print("  Available users:")
            cur.execute(
                "SELECT email, role FROM \"user\" "
                "WHERE email NOT LIKE '%%onyxapikey.ai' "
                "ORDER BY email"
            )
            for row in cur.fetchall():
                print(f"    {row['email']}  (role: {row['role']})")
            sys.exit(1)

        print(f"\nTarget user:")
        print(f"  Email: {target_user['email']}")
        print(f"  Role:  {target_user['role']}")
        print(f"  UUID:  {target_user['id']}")

        # ── Step 6: Check if already mapped ──────────────────────────────
        if str(old_user_id) == str(target_user["id"]):
            print(f"\n[OK] API key is already mapped to {args.email}. Nothing to do.")
            sys.exit(0)

        # ── Step 7: Perform the remapping ────────────────────────────────
        print(f"\nRemapping:")
        print(f"  api_key.user_id:  {old_user_id}  -->  {target_user['id']}")
        print(f"  api_key.owner_id: {api_key_row['owner_id']}  -->  {target_user['id']}")

        if args.dry_run:
            print("\n[DRY RUN] No changes made.")
            sys.exit(0)

        cur.execute(
            "UPDATE api_key SET user_id = %s, owner_id = %s WHERE id = %s",
            (target_user["id"], target_user["id"], api_key_row["id"]),
        )

        # ── Step 8: Optionally clean up orphaned synthetic user ──────────
        if args.cleanup and synthetic_user:
            # Only delete if it's actually a synthetic API key user
            if "onyxapikey.ai" in synthetic_user["email"]:
                cur.execute(
                    "DELETE FROM \"user\" WHERE id = %s",
                    (old_user_id,),
                )
                print(f"  Deleted orphaned synthetic user: {synthetic_user['email']}")
            else:
                print(f"  Skipped cleanup: {synthetic_user['email']} is not a synthetic user")

        conn.commit()
        print(f"\n[SUCCESS] API key is now mapped to {args.email}")
        print(f"  All operations using this API key will be attributed to {args.email}")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
