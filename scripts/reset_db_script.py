import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

load_dotenv()

dbname = os.getenv('POSTGRES_DB', 'gts')
user = os.getenv('POSTGRES_USER', 'postgres')
password = os.getenv('POSTGRES_PASSWORD', '1234')
host = os.getenv('POSTGRES_HOST', 'localhost')
port = os.getenv('POSTGRES_PORT', '5432')

def reset_db():
    # Connect to 'postgres' db to drop 'gts'
    con = psycopg2.connect(dbname='postgres', user=user, host=host, password=password, port=port)
    con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = con.cursor()
    
    print(f"Dropping database {dbname}...")
    try:
        cur.execute(f"DROP DATABASE IF EXISTS {dbname} WITH (FORCE);")
    except Exception as e:
        print(f"Error dropping DB: {e}")

    print(f"Creating database {dbname}...")
    cur.execute(f"CREATE DATABASE {dbname};")
    
    cur.close()
    con.close()
    print("Database reset successfully.")

if __name__ == "__main__":
    reset_db()
