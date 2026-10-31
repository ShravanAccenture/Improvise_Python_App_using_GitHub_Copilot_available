import hashlib
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

app = FastAPI()
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Validate the text supplied in the JSON request body.
class TextData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str


def generate(text: str) -> str:
    """Generate a SHA-256 checksum from UTF-8 text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@app.get("/")
def read_root():
    return {"message": "Welcome to the API! Developed by GitHub Copilot"}


@app.get("/welcome", response_class=FileResponse, include_in_schema=False)
def welcome_page():
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")


@app.get("/generate/", include_in_schema=False)
@app.get("/generate", summary="Generate a checksum from query text")
def generate_from_query(text: str):
    """Return the SHA-256 checksum of the required text query parameter."""
    return {"checksum": generate(text)}


# Accept JSON text and reuse the checksum generator.
@app.post("/generate/", include_in_schema=False)
@app.post("/generate", summary="Generate a text checksum")
def generate_checksum(data: TextData):
    """Return the SHA-256 checksum of the supplied text."""
    return {"checksum": generate(data.text)}