import os
import sys
import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Add the project root to the Python path to ensure robust imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import create_db_and_tables
from app.routers import users, applications, admin
# Import the 'sio' instance from the websockets file
from app.websockets import sio
from ml.model import train_and_save_model

# --- Main Application Setup ---
# 1. Create the FastAPI app instance. This is now the primary application.
app = FastAPI(title="AI Credit Underwriting System")

# 2. Create necessary directories on startup
os.makedirs("uploads", exist_ok=True)
os.makedirs("reports", exist_ok=True)
os.makedirs("models_trained", exist_ok=True)

# 3. Configure a SINGLE, CENTRALIZED CORS middleware. This will handle both
#    regular API requests and the WebSocket connection handshake, fixing all errors.
origins = [
    "http://localhost:8001",
    "http://127.0.0.1:8001",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Create a separate ASGI application for the Socket.IO server.
socket_app = socketio.ASGIApp(sio)

# 5. Define FastAPI startup events.
@app.on_event("startup")
def on_startup():
    """On server startup, create database tables and pre-train the AI model."""
    create_db_and_tables()
    train_and_save_model()

# 6. Mount static file directories FIRST.
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/reports", StaticFiles(directory="reports"), name="reports")

# 7. Include ALL API routers AFTER static files are mounted.
app.include_router(users.router, prefix="/api", tags=["Users"])
app.include_router(applications.router, prefix="/api", tags=["Applications"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

@app.get("/api/health")
def health_check():
    """A simple endpoint to confirm the API is running."""
    return {"status": "ok"}

# 8. Mount the socket_app at the specific '/socket.io' path. This is a stable
#    integration method that keeps API and WebSocket traffic separate.
app.mount("/socket.io", socket_app)

