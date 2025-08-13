from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from environs import Env


env = Env()
DATABASE_URL = env('DATABASE_URL')

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
