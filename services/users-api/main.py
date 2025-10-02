# users-api/main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()


class User(BaseModel):
    id: Optional[int] = None
    name: str
    email: str


# --- Base de Dados em Memória ---
# Criamos uma lista de usuários/autores que correspondem exatamente
# aos 'author_id' que estão na API de livros.
# Isso garante que a chamada de uma API para a outra funcione.
users_db: List[User] = [
    User(id=1, name="Douglas Adams", email="douglas.adams@example.com"),
    User(id=2, name="George Orwell", email="george.orwell@example.com"),
    User(id=3, name="Frank Herbert", email="frank.herbert@example.com")
]

# O contador de ID começa do próximo número disponível.
user_id_counter: int = 4


# --- Endpoints da API de Usuários ---

@app.get("/users", response_model=List[User])
def read_users():
    """Retorna a lista de todos os usuários."""
    return users_db


@app.post("/users", response_model=User, status_code=201)
def create_user(user: User):
    """Cria um novo usuário."""
    global user_id_counter
    user.id = user_id_counter
    user_id_counter += 1
    users_db.append(user)
    return user


@app.get("/users/{user_id}", response_model=User)
def read_user(user_id: int):
    """
    Busca e retorna um usuário específico pelo seu ID.
    Este é o endpoint que a API de livros irá chamar.
    """
    user = next((user for user in users_db if user.id == user_id), None)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put("/users/{user_id}", response_model=User)
def update_user(user_id: int, user_update: User):
    """Atualiza as informações de um usuário existente."""
    idx = next((i for i, u in enumerate(users_db) if u.id == user_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_update.id = user_id
    users_db[idx] = user_update
    return user_update


@app.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int):
    """Deleta um usuário."""
    idx = next((i for i, u in enumerate(users_db) if u.id == user_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    users_db.pop(idx)
    # Retorna uma resposta vazia com status 204 No Content
    return
