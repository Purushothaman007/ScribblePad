from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
load_dotenv()

# Create a base class for your models
Base = declarative_base()

# Define the "users" table
class User(Base):
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True)  # Auto-incrementing primary key
    email = Column(String, nullable=False)  # Character varying, not nullable
    password_hash = Column(String, nullable=False)  # Character varying, not nullable
    username = Column(String, nullable=False)  # Character varying, not nullable


# Define the "notes" table
class Note(Base):
    __tablename__ = "notes"
    
    note_id = Column(Integer, primary_key=True)  # Auto-incrementing primary key
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)  # Foreign key to users.user_id
    title = Column(String, nullable=False)  # Character varying, not nullable
    content = Column(Text)  # Text, nullable
    created_at = Column(DateTime, default=func.now())  # Timestamp, default now()
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())  # Timestamp, default now(), updated on change
    is_pinned = Column(Boolean, default=False)  # Boolean, default false
    reminder_date = Column(DateTime)  # Date, nullable
    tags = Column(String)  # Character varying, nullable
    email_sent = Column(Boolean, default=False)  # Boolean, default false

  

# Database connection setup
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the tables in the database
Base.metadata.create_all(bind=engine)