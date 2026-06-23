import os
import secrets
from dotenv import load_dotenv

load_dotenv()


def build_database_url():
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return database_url

    db_password = os.getenv('POSTGRES_PASSWORD')
    if not db_password:
        raise RuntimeError(
            'POSTGRES_PASSWORD is required. Set it in env.txt or provide DATABASE_URL.'
        )

    db_user = os.getenv('POSTGRES_USER', 'finance_user')
    db_host = os.getenv('POSTGRES_HOST', 'localhost')
    db_port = os.getenv('POSTGRES_PORT', '5432')
    db_name = os.getenv('POSTGRES_DB', 'finance_db')
    return f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or secrets.token_hex(32)

    SQLALCHEMY_DATABASE_URI = build_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False