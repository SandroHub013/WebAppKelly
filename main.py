from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from routers import calcola, backtest, heatmap

# Get the absolute path of the current file's directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()

# Mount static files using absolute paths
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.mount("/assets", StaticFiles(directory=os.path.join(BASE_DIR, "assets")), name="assets")

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app.include_router(calcola.router)
app.include_router(backtest.router)
app.include_router(heatmap.router)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Add a simple endpoint to test
@app.get("/hello")
def hello():
    return {"message": "Hello World"} 