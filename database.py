from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "postgresql://postgres.kylfmdpdqoeyvgkvzjda:khondoker11@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres"

engine = create_engine(SQLALCHEMY_DATABASE_URL,echo=True)

SessionLocal = sessionmaker( autoflush=False, autocommit=False, bind=engine)

Base = declarative_base()