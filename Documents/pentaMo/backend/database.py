from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from config.settings import settings
from db.models import Base

# Database setup
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _check_add_columns_to_sqlite():
    """Manual migration for SQLite to add positive/negative feedback columns if missing"""
    if "sqlite" not in settings.database_url:
        return
        
    inspector = inspect(engine)
    with engine.connect() as conn:
        # Check chat_messages table
        cm_columns = [c['name'] for c in inspector.get_columns('chat_messages')]
        if 'positive_feedback_count' not in cm_columns:
            conn.execute(text("ALTER TABLE chat_messages ADD COLUMN positive_feedback_count INTEGER DEFAULT 0"))
            conn.commit()
        if 'negative_feedback_count' not in cm_columns:
            conn.execute(text("ALTER TABLE chat_messages ADD COLUMN negative_feedback_count INTEGER DEFAULT 0"))
            conn.commit()
            
        # Check users table for password_hash
        user_columns = [c['name'] for c in inspector.get_columns('users')]
        if 'password_hash' not in user_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR"))
            conn.commit()

def create_tables():
    Base.metadata.create_all(bind=engine)
    # Post-creation migration check for existing databases
    try:
        _check_add_columns_to_sqlite()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Metadata migration warning: {e}")
