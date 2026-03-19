import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pathlib import Path
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

import os
BASE_DIR = Path(__file__).resolve().parent.parent

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "frontend")), name="static")

@app.get("/")
def root():
    return FileResponse(str(BASE_DIR / "frontend" / "index.html"))

if __name__ == "__main__":
    import uvicorn
    # Railway provides the port via an environment variable
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)