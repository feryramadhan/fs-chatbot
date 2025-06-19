from fastapi import FastAPI
from app.services import socket

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

app.include_router(socket.router)
