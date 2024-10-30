from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database URL construction
DB_USER = os.getenv('DB_USER', 'admin')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'admin123')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'knowledge_base')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SQLAlchemy setup
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    echo=False  # Set to True for SQL query logging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Database session generator"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)