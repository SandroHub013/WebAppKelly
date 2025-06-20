from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from routers import calcola, backtest, heatmap

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

templates = Jinja2Templates(directory="templates")

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