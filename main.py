from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI()

# Sample data model for demonstration
class Item(BaseModel):
    name: str
    description: str = None
    price: float
    tax: float = None

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the FastAPI Backend!"}

# Example of a GET request
@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "query": q}

# Example of a POST request
@app.post("/items/")
def create_item(item: Item):
    return {"item": item}


if __name__ == "__main__":
    port = int("PORT", 8000)
    uvicorn.run(app, host="0.0.0.0", port=port)