# books/main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import httpx
import requests

app = FastAPI()


class Book(BaseModel):
    id: Optional[int] = None
    title: str
    author_id: int
    description: Optional[str] = None
    price: float


class Author(BaseModel):
    id: int
    name: str
    email: str


books_db: List[Book] = [
    Book(id=1, title="O Guia do Mochileiro das Galáxias", author_id=1, description="A comédia de ficção científica mais engraçada já escrita.", price=42.0),
    Book(id=2, title="1984", author_id=2, description="Um futuro distópico onde o Grande Irmão está sempre observando.", price=35.50),
    Book(id=3, title="Duna", author_id=3, description="Uma épica saga de ficção científica sobre poder, religião e ecologia.", price=59.90)
]

book_id_counter: int = 4


@app.get("/books", response_model=List[Book])
def read_books():
    return books_db


@app.post("/books", response_model=Book, status_code=201)
def create_book(book: Book):
    global book_id_counter
    book.id = book_id_counter
    book_id_counter += 1
    books_db.append(book)
    return book


@app.get("/books/{book_id}", response_model=Book)
def read_book(book_id: int):
    book = next((book for book in books_db if book.id == book_id), None)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.put("/books/{book_id}", response_model=Book)
def update_book(book_id: int, book: Book):
    idx = next((i for i, b in enumerate(books_db) if b.id == book_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Book not found")
    books_db[idx] = book
    return book


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    idx = next((i for i, b in enumerate(books_db) if b.id == book_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Book not found")
    books_db.pop(idx)
    return {"message": "Book deleted successfully"}


@app.get("/books/{book_id}/user", response_model=Author)
async def get_user_for_book_async(book_id: int):
    # Nota: para este endpoint funcionar, a API de usuários precisa ter usuários
    # com os IDs 1, 2 e 3 para corresponder aos autores dos livros.
    async with httpx.AsyncClient() as client:
        # O ideal seria usar uma variável de ambiente para a URL da API de usuários
        response = await client.get(f"http://users-api.basics:9001/users/{book_id}")
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=404, detail="User not found")


@app.get("/books/{book_id}/user_sync", response_model=Author)
def get_user_for_book_sync(book_id: int):
    response = requests.get(f"http://users-api.basics:9001/users/{book_id}")
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=404, detail="User not found")
