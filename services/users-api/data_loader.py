#!/usr/bin/env python3
# data_loader.py
"""
Script para carregar dados do CSV para o banco de dados PostgreSQL
com embeddings gerados pelo AWS Bedrock
"""

import os
import csv
import sys
from typing import List, Dict
from database import db_connection
from vector_search import vector_search
from sqlalchemy import text

def load_csv_data(csv_path: str) -> List[Dict]:
    """
    Carrega dados do arquivo CSV

    Args:
        csv_path: Caminho para o arquivo CSV

    Returns:
        Lista de dicionários com os dados
    """
    authors = []

    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                authors.append({
                    'name': row['name'],
                    'email': row['email'],
                    'bio': row['bio'],
                    'expertise': row['expertise']
                })

        print(f"Carregados {len(authors)} autores do CSV")
        return authors

    except FileNotFoundError:
        print(f"Erro: Arquivo {csv_path} não encontrado")
        sys.exit(1)
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
        sys.exit(1)

def check_existing_authors(db_session) -> int:
    """
    Verifica quantos autores já existem no banco

    Args:
        db_session: Sessão do banco de dados

    Returns:
        Número de autores existentes
    """
    result = db_session.execute(text("SELECT COUNT(*) as count FROM authors"))
    row = result.fetchone()
    return row.count if row else 0

def clear_existing_data(db_session):
    """
    Remove todos os autores existentes (usar com cuidado!)

    Args:
        db_session: Sessão do banco de dados
    """
    try:
        db_session.execute(text("TRUNCATE TABLE authors RESTART IDENTITY CASCADE"))
        db_session.commit()
        print("Dados existentes removidos")
    except Exception as e:
        db_session.rollback()
        print(f"Erro ao limpar dados: {e}")
        raise

def load_authors_to_database(authors: List[Dict], force_reload: bool = False):
    """
    Carrega autores no banco de dados com embeddings

    Args:
        authors: Lista de autores
        force_reload: Se True, limpa dados existentes antes de carregar
    """
    # Conectar ao banco
    db_connection.connect()
    db_session = db_connection.get_session()

    try:
        # Verificar autores existentes
        existing_count = check_existing_authors(db_session)

        if existing_count > 0:
            if force_reload:
                print(f"Removendo {existing_count} autores existentes...")
                clear_existing_data(db_session)
            else:
                print(f"Já existem {existing_count} autores no banco.")
                print("Use --force para recarregar os dados")
                return

        # Carregar autores
        print(f"\nCarregando {len(authors)} autores...")
        loaded = 0
        failed = 0

        for idx, author in enumerate(authors, 1):
            try:
                print(f"[{idx}/{len(authors)}] Processando: {author['name']}...", end=" ")

                vector_search.add_author_with_embedding(
                    db=db_session,
                    name=author['name'],
                    email=author['email'],
                    bio=author['bio'],
                    expertise=author['expertise']
                )

                loaded += 1
                print("OK")

            except Exception as e:
                failed += 1
                print(f"ERRO: {str(e)}")

        print(f"\nResultado:")
        print(f"  - Carregados com sucesso: {loaded}")
        print(f"  - Falhas: {failed}")

    except Exception as e:
        print(f"Erro durante o carregamento: {e}")
        db_session.rollback()
        raise

    finally:
        db_session.close()
        db_connection.close()

def main():
    """Função principal"""
    print("=" * 60)
    print("Data Loader - Authors API with Vector Search")
    print("=" * 60)

    # Verificar argumentos
    force_reload = "--force" in sys.argv

    # Caminho do CSV
    csv_path = os.path.join(os.path.dirname(__file__), "sample_data.csv")

    # Verificar variáveis de ambiente
    if not os.getenv("AWS_REGION"):
        print("Aviso: AWS_REGION não definida, usando us-east-2")
        os.environ["AWS_REGION"] = "us-east-2"

    # Carregar CSV
    print(f"\nCarregando dados de: {csv_path}")
    authors = load_csv_data(csv_path)

    # Carregar no banco
    print(f"\nConectando ao banco de dados...")
    load_authors_to_database(authors, force_reload=force_reload)

    print("\nCarga de dados concluída!")

if __name__ == "__main__":
    main()
