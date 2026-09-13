"""
CleanRoute AI — Database Connectivity & Initialization Helper
Checks PostgreSQL connection using credentials in backend/.env and creates cleanroute_db if missing.
"""

import os
import sys
from dotenv import load_dotenv
import psycopg

load_dotenv()

user = os.getenv('DATABASE_USER', 'postgres')
password = os.getenv('DATABASE_PASSWORD', '')
host = os.getenv('DATABASE_HOST', 'localhost')
port = os.getenv('DATABASE_PORT', '5432')
dbname = os.getenv('DATABASE_NAME', 'cleanroute_db')

print(f"Checking PostgreSQL server connection at {host}:{port} as user '{user}'...")

try:
    with psycopg.connect(user=user, password=password, host=host, port=port, autocommit=True) as conn:
        print("[OK] Connected to PostgreSQL server successfully!")
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
            if cur.fetchone():
                print(f"[OK] Database '{dbname}' already exists.")
            else:
                print(f"Creating database '{dbname}'...")
                cur.execute(f'CREATE DATABASE "{dbname}"')
                print(f"[OK] Database '{dbname}' created successfully!")
except psycopg.OperationalError as err:
    print(f"\n[CONNECTION ERROR]: {err}")
    print("\nTip: Please ensure DATABASE_PASSWORD in backend/.env matches the password you entered when installing PostgreSQL.")
    sys.exit(1)
