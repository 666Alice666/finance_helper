import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-for-coursework')

    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://finance_user:12345@localhost:5432/finance_db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False