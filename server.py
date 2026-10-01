"""Serveur local : python3 -m uvicorn server:app --port 8000  ->  http://localhost:8000"""
import os

from fastapi.staticfiles import StaticFiles

from api.index import app

app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), "public"), html=True), name="public")
