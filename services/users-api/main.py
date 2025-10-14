# users-api/main.py

from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.orm import Session

from database import get_db, db_connection
from vector_search import vector_search
from bedrock_client import bedrock_client

app = FastAPI(
    title="Authors API with Vector Search",
    description="API de autores com busca vetorial usando AWS Bedrock e RDS PostgreSQL com pgvector",
    version="2.0.0"
)

# Modelos Pydantic
class AuthorBase(BaseModel):
    name: str = Field(..., description="Nome do autor")
    email: str = Field(..., description="Email do autor")
    bio: str = Field(..., description="Biografia do autor")
    expertise: str = Field(..., description="Áreas de expertise do autor")

class AuthorCreate(AuthorBase):
    pass

class Author(AuthorBase):
    id: int

    class Config:
        from_attributes = True

class AuthorSearchResult(Author):
    similarity_score: float = Field(..., description="Score de similaridade (0-1)")

class SearchQuery(BaseModel):
    query: str = Field(..., description="Texto da busca")
    top_k: int = Field(5, ge=1, le=20, description="Número de resultados")
    similarity_threshold: float = Field(0.0, ge=0.0, le=1.0, description="Threshold de similaridade")

class QuestionRequest(BaseModel):
    question: str = Field(..., description="Pergunta sobre autores")
    top_k: int = Field(3, ge=1, le=10, description="Número de autores para contexto")

class QuestionResponse(BaseModel):
    question: str
    answer: str
    context_authors: List[Author]


# Eventos de inicialização e finalização
@app.on_event("startup")
async def startup_event():
    """Inicializa conexão com o banco de dados"""
    db_connection.connect()
    print("Conexão com banco de dados estabelecida")

@app.on_event("shutdown")
async def shutdown_event():
    """Fecha conexão com o banco de dados"""
    db_connection.close()
    print("Conexão com banco de dados fechada")


# --- Endpoints da API ---

@app.get("/")
def root():
    """Endpoint raiz com informações da API"""
    return {
        "name": "Authors API with Vector Search",
        "version": "2.0.0",
        "features": [
            "Vector search using AWS Bedrock embeddings",
            "PostgreSQL with pgvector extension",
            "Semantic search for authors",
            "AI-powered Q&A with Bedrock"
        ]
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# --- Endpoints de Autores ---

@app.get("/authors", response_model=List[Author])
def get_authors(
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Retorna lista de todos os autores"""
    authors = vector_search.get_all_authors(db, limit=limit)
    return authors

@app.get("/authors/{author_id}", response_model=Author)
def get_author(author_id: int, db: Session = Depends(get_db)):
    """Busca um autor por ID"""
    author = vector_search.get_author_by_id(db, author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    return author

@app.post("/authors", response_model=Author, status_code=201)
def create_author(author: AuthorCreate, db: Session = Depends(get_db)):
    """
    Cria um novo autor com embedding gerado automaticamente
    O embedding é criado usando AWS Bedrock a partir da bio e expertise
    """
    try:
        created_author = vector_search.add_author_with_embedding(
            db=db,
            name=author.name,
            email=author.email,
            bio=author.bio,
            expertise=author.expertise
        )
        return created_author
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating author: {str(e)}")


# --- Endpoints de Vector Search ---

@app.post("/search/text", response_model=List[AuthorSearchResult])
def search_authors_by_text(
    search: SearchQuery,
    db: Session = Depends(get_db)
):
    """
    Cenário 1: Bedrock -> Vector Search

    Busca autores usando texto natural. O fluxo é:
    1. Texto enviado para AWS Bedrock
    2. Bedrock gera embedding do texto
    3. Embedding é usado para busca vetorial no PostgreSQL
    4. Retorna autores mais similares
    """
    try:
        results = vector_search.search_by_text(
            db=db,
            query_text=search.query,
            top_k=search.top_k,
            similarity_threshold=search.similarity_threshold
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@app.post("/ask", response_model=QuestionResponse)
def ask_question(
    request: QuestionRequest,
    db: Session = Depends(get_db)
):
    """
    Cenário 2: Vector Search -> Bedrock

    Responde perguntas sobre autores. O fluxo é:
    1. Pergunta é convertida em embedding pelo Bedrock
    2. Vector search encontra autores relevantes no PostgreSQL
    3. Autores encontrados são enviados como contexto para o Bedrock
    4. Bedrock (Nova Micro) gera resposta baseada no contexto
    5. Retorna resposta com os autores utilizados como contexto
    """
    try:
        # Buscar autores relevantes usando vector search
        results = vector_search.search_by_text(
            db=db,
            query_text=request.question,
            top_k=request.top_k,
            similarity_threshold=0.3
        )

        if not results:
            raise HTTPException(
                status_code=404,
                detail="No relevant authors found for this question"
            )

        # Usar Bedrock para gerar resposta com contexto dos autores
        answer = bedrock_client.answer_question_with_context(
            question=request.question,
            context_authors=results
        )

        return QuestionResponse(
            question=request.question,
            answer=answer,
            context_authors=results
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")


@app.get("/authors/{author_id}/summary")
def get_author_summary(author_id: int, db: Session = Depends(get_db)):
    """
    Gera um resumo do perfil de um autor usando Bedrock
    """
    author = vector_search.get_author_by_id(db, author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    try:
        summary = bedrock_client.summarize_author_profile(
            name=author["name"],
            bio=author["bio"],
            expertise=author["expertise"]
        )

        return {
            "author": author,
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")


# Manter compatibilidade com endpoints antigos (legado)
@app.get("/users", response_model=List[Author])
def read_users_legacy(db: Session = Depends(get_db)):
    """Endpoint legado - retorna autores"""
    return get_authors(limit=100, db=db)

@app.get("/users/{user_id}", response_model=Author)
def read_user_legacy(user_id: int, db: Session = Depends(get_db)):
    """Endpoint legado - busca autor por ID"""
    return get_author(author_id=user_id, db=db)
