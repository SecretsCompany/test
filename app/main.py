from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from .database import engine, Base
from . import models
from .routers import users, investments, admin
from .seed import seed_db

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CryptoInvest API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(investments.router)
app.include_router(admin.router)

frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/dashboard")
    def serve_dashboard():
        return FileResponse(os.path.join(frontend_dir, "dashboard.html"))

    @app.get("/admin")
    def serve_admin():
        return FileResponse(os.path.join(frontend_dir, "admin.html"))

    @app.get("/login")
    def serve_login():
        return FileResponse(os.path.join(frontend_dir, "login.html"))


@app.on_event("startup")
def on_startup():
    seed_db()
