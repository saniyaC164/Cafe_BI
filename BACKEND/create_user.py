import bcrypt
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

email    = "admin@brewanalytics.com"
password = "admin123"
name     = "Admin"

hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

with engine.connect() as conn:
    conn.execute(text("""
        INSERT INTO users (email, name, password_hash, role)
        VALUES (:email, :name, :hash, 'admin')
        ON CONFLICT (email) DO NOTHING
    """), {"email": email, "name": name, "hash": hashed})
    conn.commit()
    print(f"User created: {email} / {password}")