from sqlmodel import create_engine, Session

DATABASE_URL = "sqlite:///./database.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

def create_db_and_tables():
    from . import models # Local import to avoid circular dependency
    models.SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

def SessionLocal():
    return Session(engine)

