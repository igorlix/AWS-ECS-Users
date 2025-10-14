# database.py
import os
import json
import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from typing import Optional

Base = declarative_base()

class DatabaseConnection:
    """Gerencia a conexão com o RDS PostgreSQL com pgvector"""

    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._db_config = None

    def _get_db_credentials(self) -> dict:
        """Obtém credenciais do RDS do Secrets Manager"""
        if self._db_config:
            return self._db_config

        secret_arn = os.getenv("DB_SECRET_ARN")
        aws_region = os.getenv("AWS_REGION", "us-east-2")

        # Se não tiver secret ARN, usar configuração local
        if not secret_arn:
            self._db_config = {
                "host": os.getenv("DB_HOST", "localhost"),
                "port": int(os.getenv("DB_PORT", "5432")),
                "dbname": os.getenv("DB_NAME", "vectordb"),
                "username": os.getenv("DB_USERNAME", "dbadmin"),
                "password": os.getenv("DB_PASSWORD", "password")
            }
            return self._db_config

        # Obter credenciais do Secrets Manager
        client = boto3.client("secretsmanager", region_name=aws_region)

        try:
            response = client.get_secret_value(SecretId=secret_arn)
            secret = json.loads(response["SecretString"])

            self._db_config = {
                "host": secret["host"],
                "port": secret["port"],
                "dbname": secret["dbname"],
                "username": secret["username"],
                "password": secret["password"]
            }
            return self._db_config

        except Exception as e:
            print(f"Erro ao obter credenciais do Secrets Manager: {e}")
            raise

    def get_connection_string(self) -> str:
        """Retorna a string de conexão PostgreSQL"""
        creds = self._get_db_credentials()
        return (
            f"postgresql://{creds['username']}:{creds['password']}"
            f"@{creds['host']}:{creds['port']}/{creds['dbname']}"
        )

    def connect(self):
        """Estabelece conexão com o banco de dados"""
        if self.engine:
            return

        connection_string = self.get_connection_string()

        # Criar engine do SQLAlchemy
        self.engine = create_engine(
            connection_string,
            poolclass=NullPool,
            echo=False
        )

        # Criar sessionmaker
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        # Verificar conexão e habilitar extensão pgvector
        self._initialize_database()

    def _initialize_database(self):
        """Inicializa o banco de dados com extensões necessárias"""
        with self.engine.connect() as conn:
            # Habilitar extensão pgvector
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()

            # Criar tabela de autores se não existir
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS authors (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    bio TEXT,
                    expertise TEXT,
                    embedding vector(1024),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()

            # Criar índice para busca vetorial
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS authors_embedding_idx
                ON authors
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """))
            conn.commit()

    def get_session(self):
        """Retorna uma nova sessão do banco de dados"""
        if not self.SessionLocal:
            self.connect()
        return self.SessionLocal()

    def close(self):
        """Fecha a conexão com o banco de dados"""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.SessionLocal = None

# Instância global de conexão
db_connection = DatabaseConnection()

def get_db():
    """Dependency injection para FastAPI"""
    db = db_connection.get_session()
    try:
        yield db
    finally:
        db.close()
