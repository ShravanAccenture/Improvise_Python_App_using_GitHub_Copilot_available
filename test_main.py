"""Exercise the checksum routes through FastAPI's HTTP test client."""

from hashlib import sha256
from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    with TestClient(app, follow_redirects=False) as test_client:
        yield test_client


@pytest.mark.parametrize("text", ["abc", "", "  hello\n", "caf\u00e9 \U0001f600"])
def test_generate_get(client, text):
    response = client.get("/generate", params={"text": text})

    assert response.status_code == 200
    assert response.json() == {"checksum": sha256(text.encode("utf-8")).hexdigest()}


@pytest.mark.parametrize("text", ["abc", "", "  hello\n", "caf\u00e9 \U0001f600"])
def test_generate_post(client, text):
    response = client.post("/generate", json={"text": text})

    assert response.status_code == 200
    assert response.json() == {"checksum": sha256(text.encode("utf-8")).hexdigest()}
    assert response.json() == client.get("/generate", params={"text": text}).json()


def test_generate_known_checksum(client):
    response = client.post("/generate", json={"text": "abc"})

    assert response.json() == {
        "checksum": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    }


def test_generate_trailing_slash_aliases(client):
    expected = {"checksum": sha256(b"abc").hexdigest()}
    get_response = client.get("/generate/", params={"text": "abc"})
    post_response = client.post("/generate/", json={"text": "abc"})

    assert get_response.status_code == 200
    assert post_response.status_code == 200
    assert get_response.json() == expected
    assert post_response.json() == expected


@pytest.mark.parametrize(
    "body",
    [{}, {"text": None}, {"text": 123}, {"text": True}, {"text": []},
     {"text": {}}, {"text": "hello", "extra": "not allowed"}],
)
def test_generate_post_rejects_invalid_body(client, body):
    assert client.post("/generate", json=body).status_code == 422


def test_generate_post_requires_body(client):
    assert client.post("/generate").status_code == 422


def test_generate_post_rejects_malformed_json(client):
    response = client.post(
        "/generate", content='{"text":', headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422


def test_generate_get_requires_text(client):
    assert client.get("/generate").status_code == 422


def test_welcome(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "GitHub Copilot" in response.json()["message"]


def test_welcome_page_and_local_links(client):
    class LinkParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.paths = []

        def handle_starttag(self, tag, attrs):
            for name, value in attrs:
                if name in {"href", "src"} and value and value.startswith("/"):
                    self.paths.append(value)

    response = client.get("/welcome")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    parser = LinkParser()
    parser.feed(response.text)
    assert "/static/style.css" in parser.paths
    assert "/docs" in parser.paths
    for path in parser.paths:
        assert client.get(path).status_code == 200
    assert client.get("/static/style.css").headers["content-type"].startswith("text/css")


def test_api_documentation(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    response = client.get("/openapi.json")

    assert response.status_code == 200
    operation = response.json()["paths"]["/generate"]["post"]
    assert operation["requestBody"]["required"] is True
    assert "application/json" in operation["requestBody"]["content"]