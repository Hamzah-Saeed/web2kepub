# app.py
from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, HTMLResponse
from pipeline import url_to_kepub
import webbrowser
import threading
import uvicorn

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def index():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/convert")
def convert(url: str = Form(...)):
    kepub_path = url_to_kepub(url)

    return FileResponse(
        kepub_path,
        filename="article.kepub.epub",
        media_type="application/epub+zip"
    )

def run():
    threading.Timer(
        1.0,
        lambda: webbrowser.open("http://127.0.0.1:8000")
    ).start()

    uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    run()