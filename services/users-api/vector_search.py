# vector_search.py
from typing import List, Dict, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from bedrock_client import bedrock_client

class VectorSearchService:
    """Serviço para operações de busca vetorial"""

    @staticmethod
    def search_similar_authors(
        db: Session,
        query_embedding: List[float],
        top_k: int = 5,
        similarity_threshold: float = 0.0
    ) -> List[Dict]:
        """
        Busca autores similares usando cosine similarity

        Args:
            db: Sessão do banco de dados
            query_embedding: Vetor de embedding da consulta
            top_k: Número de resultados a retornar
            similarity_threshold: Threshold mínimo de similaridade (0-1)

        Returns:
            Lista de autores com score de similaridade
        """
        # Converter embedding para formato PostgreSQL
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        # Query SQL com busca vetorial usando cosine similarity
        query = text("""
            SELECT
                id,
                name,
                email,
                bio,
                expertise,
                1 - (embedding <=> :query_embedding::vector) AS similarity_score
            FROM authors
            WHERE embedding IS NOT NULL
                AND 1 - (embedding <=> :query_embedding::vector) > :threshold
            ORDER BY embedding <=> :query_embedding::vector
            LIMIT :top_k
        """)

        result = db.execute(
            query,
            {
                "query_embedding": embedding_str,
                "threshold": similarity_threshold,
                "top_k": top_k
            }
        )

        authors = []
        for row in result:
            authors.append({
                "id": row.id,
                "name": row.name,
                "email": row.email,
                "bio": row.bio,
                "expertise": row.expertise,
                "similarity_score": float(row.similarity_score)
            })

        return authors

    @staticmethod
    def search_by_text(
        db: Session,
        query_text: str,
        top_k: int = 5,
        similarity_threshold: float = 0.0
    ) -> List[Dict]:
        """
        Busca autores usando uma consulta de texto

        Args:
            db: Sessão do banco de dados
            query_text: Texto da consulta
            top_k: Número de resultados
            similarity_threshold: Threshold de similaridade

        Returns:
            Lista de autores similares
        """
        # Gerar embedding da consulta usando Bedrock
        query_embedding = bedrock_client.generate_embedding(query_text)

        # Buscar autores similares
        return VectorSearchService.search_similar_authors(
            db=db,
            query_embedding=query_embedding,
            top_k=top_k,
            similarity_threshold=similarity_threshold
        )

    @staticmethod
    def add_author_with_embedding(
        db: Session,
        name: str,
        email: str,
        bio: str,
        expertise: str
    ) -> Dict:
        """
        Adiciona um novo autor com embedding gerado automaticamente

        Args:
            db: Sessão do banco de dados
            name: Nome do autor
            email: Email do autor
            bio: Biografia do autor
            expertise: Expertise do autor

        Returns:
            Dados do autor criado
        """
        # Gerar texto para embedding (combinar bio e expertise)
        text_for_embedding = f"{name}. {bio} Expertise: {expertise}"

        # Gerar embedding usando Bedrock
        embedding = bedrock_client.generate_embedding(text_for_embedding)

        # Converter embedding para formato PostgreSQL
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"

        # Inserir autor no banco
        query = text("""
            INSERT INTO authors (name, email, bio, expertise, embedding)
            VALUES (:name, :email, :bio, :expertise, :embedding::vector)
            RETURNING id, name, email, bio, expertise
        """)

        result = db.execute(
            query,
            {
                "name": name,
                "email": email,
                "bio": bio,
                "expertise": expertise,
                "embedding": embedding_str
            }
        )

        db.commit()

        row = result.fetchone()
        return {
            "id": row.id,
            "name": row.name,
            "email": row.email,
            "bio": row.bio,
            "expertise": row.expertise
        }

    @staticmethod
    def get_all_authors(db: Session, limit: int = 100) -> List[Dict]:
        """
        Retorna todos os autores do banco

        Args:
            db: Sessão do banco de dados
            limit: Limite de resultados

        Returns:
            Lista de autores
        """
        query = text("""
            SELECT id, name, email, bio, expertise
            FROM authors
            ORDER BY id
            LIMIT :limit
        """)

        result = db.execute(query, {"limit": limit})

        authors = []
        for row in result:
            authors.append({
                "id": row.id,
                "name": row.name,
                "email": row.email,
                "bio": row.bio,
                "expertise": row.expertise
            })

        return authors

    @staticmethod
    def get_author_by_id(db: Session, author_id: int) -> Optional[Dict]:
        """
        Busca um autor por ID

        Args:
            db: Sessão do banco de dados
            author_id: ID do autor

        Returns:
            Dados do autor ou None
        """
        query = text("""
            SELECT id, name, email, bio, expertise
            FROM authors
            WHERE id = :author_id
        """)

        result = db.execute(query, {"author_id": author_id})
        row = result.fetchone()

        if row:
            return {
                "id": row.id,
                "name": row.name,
                "email": row.email,
                "bio": row.bio,
                "expertise": row.expertise
            }

        return None

# Instância global
vector_search = VectorSearchService()
