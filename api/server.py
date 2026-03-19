import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from api.routes import skills, agent, dashboard

app = FastAPI(title="CareerPilot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router, prefix="/api")
app.include_router(skills.router,    prefix="/api")
app.include_router(agent.router,     prefix="/api")

app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
def root():
    return FileResponse("frontend/index.html")