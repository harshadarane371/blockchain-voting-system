import sqlite3

def connect_db():
    return sqlite3.connect("evoting.db")

def create_tables():
    conn = connect_db()
    cursor = conn.cursor()

    # Voters table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS voters (
        voter_id TEXT PRIMARY KEY,
        name TEXT,
        password TEXT,
        has_voted INTEGER DEFAULT 0,
        aadhar TEXT,
        dob TEXT
    )
    """)

    # In database.py -> create_tables()
    cursor.execute(""" CREATE TABLE IF NOT EXISTS candidates (
        candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_name TEXT,
        candidate_sign TEXT  
    )
    """)

    # Admin table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )
    """)

    # In create_tables()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS election_settings (
        phase TEXT,
        start_time TEXT,
        end_time TEXT
    )
    """)
    cursor.execute("SELECT * FROM election_settings")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO election_settings VALUES ('Setup', '', '')")

    
    


    # Blockchain table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS blockchain (
        block_index INTEGER,
        timestamp TEXT,
        data TEXT,
        previous_hash TEXT,
        hash TEXT
    )
    """)
    cursor.execute("SELECT * FROM admins WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO admins (username, password) VALUES (?, ?)", ("admin", "admin123"))

    conn.commit()
    conn.close()