# Text Checksum API

A Python learning project built with FastAPI and GitHub Copilot. It accepts text
through a query parameter or JSON request body and returns a SHA-256 checksum.
The same application serves a personalized HTML welcome page and interactive
API documentation.

For architecture, implementation details, complete API contracts, frontend
behavior, and maintenance guidance, see [documentation.md](documentation.md).

The implementation follows the activity's detailed checksum requirement:
it returns one checksum per request, not a list of language-model tokens.
The starting Python file was empty, so the shared generator and both API routes
were created during the activity.

## Features

- GET and POST endpoints sharing one checksum generator.
- Pydantic validation for a JSON body containing exactly one `text` string.
- UTF-8 support with whitespace, Unicode, and empty strings preserved.
- JSON welcome message and an HTML page personalized for Chimmani Venumuni.
- Swagger UI, ReDoc, and an automatically generated OpenAPI schema.
- HTTP tests using FastAPI `TestClient`, with warnings treated as errors.
- Static-page keyboard focus styles and reduced-motion support.

## Technology

| Component | Purpose |
| --- | --- |
| Python `hashlib` | SHA-256 checksum generation |
| FastAPI | HTTP routes, validation integration, and API documentation |
| Pydantic v2 | Request-body model and extra-field rejection |
| Uvicorn | ASGI web server |
| pytest and `httpx2` | Automated HTTP tests |
| HTML, CSS, and inline SVG | Personalized welcome page |

Dependency ranges are maintained in [requirements.txt](requirements.txt).
That file includes both application and test dependencies; it is not a lockfile.

## Project Structure

```text
copilot_lab/
|-- .gitignore          # Excludes virtual environments and generated caches
|-- main.py             # Application, request model, routes, and generator
|-- requirements.txt    # Application and test dependencies
|-- test_main.py        # HTTP regression tests
|-- README.md           # Project documentation
|-- documentation.md    # Detailed technical reference
`-- static/
	|-- index.html      # Personalized welcome page
	`-- style.css       # Layout, animation, and accessibility styles
```

Generated directories such as `.venv`, `__pycache__`, and `.pytest_cache` are
not source files and are excluded from Git.

## Prerequisites

- Python 3.11 or newer; the `httpx2` test dependency requires Python 3.11.
- pip and Python's `venv` module.
- A terminal opened in this repository's root directory.
- Optional: curl for the HTTP examples below.

The project was developed in a Linux VS Code dev container. A dev container
is not required to run the application, and this repository does not currently
include a Dockerfile or a dev-container configuration.

## Installation

Create and activate a virtual environment on Linux or macOS:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows PowerShell, use `.venv\Scripts\Activate.ps1` instead of the
`source` command. If your system provides `python3` rather than `python`, use
`python3` to create the virtual environment.

No database, API key, or application environment variables are required.

## Run With Uvicorn

From the repository root with the virtual environment active:

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

`main:app` refers to the `app` object in [main.py](main.py). `--reload` restarts
the server when source code changes and should only be used for development.
The `0.0.0.0` binding makes the server reachable through container port forwarding;
use `--host 127.0.0.1` to restrict access to the local machine outside a container.

| URL | Purpose |
| --- | --- |
| http://localhost:8000/ | JSON welcome message |
| http://localhost:8000/welcome | HTML welcome page |
| http://localhost:8000/docs | Interactive Swagger UI |
| http://localhost:8000/redoc | ReDoc reference |
| http://localhost:8000/openapi.json | OpenAPI schema |

In a dev container or Codespace, forward port 8000 through VS Code's Ports panel
and use the forwarded address when localhost is not accessible from your browser.
Press `Ctrl+C` in the server terminal to stop Uvicorn. Run `deactivate` to leave
the virtual environment when finished.

## API Reference

| Method | Path | Input | Successful response |
| --- | --- | --- | --- |
| GET | `/` | None | JSON welcome message |
| GET | `/welcome` | None | HTML welcome page |
| GET | `/generate` | Required `text` query parameter | JSON checksum |
| POST | `/generate` | Required JSON body with one `text` string | JSON checksum |
| GET | `/static/style.css` | None | Page stylesheet |

Both checksum routes also accept `/generate/` without redirects. The trailing-slash
aliases and HTML welcome route are omitted from OpenAPI to keep its API listing
focused; static assets are served through a mounted application.

### GET Example

Use URL encoding when sending text containing spaces or special characters:

```bash
curl --get http://localhost:8000/generate \
	--data-urlencode 'text=abc'
```

### POST Example

```bash
curl http://localhost:8000/generate \
	-H 'Content-Type: application/json' \
	-d '{"text": "abc"}'
```

Both examples return HTTP 200 and the same checksum:

```json
{
	"checksum": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
}
```

### Validation

The POST body must be a JSON object containing exactly one field named `text`.
Its value must be a string. An empty string is valid; text is not trimmed or
normalized before hashing.

| Input | Result |
| --- | --- |
| `{"text": "hello"}` | HTTP 200 |
| `{"text": ""}` | HTTP 200 |
| `{}` or no request body | HTTP 422 |
| `{"text": null}` or `{"text": 123}` | HTTP 422 |
| `{"text": "hello", "extra": true}` | HTTP 422 |
| Malformed JSON | HTTP 422 |
| GET `/generate` without a `text` query parameter | HTTP 422 |

For example, inspect a validation response with:

```bash
curl -i http://localhost:8000/generate \
	-H 'Content-Type: application/json' \
	-d '{"text": null}'
```

Validation responses include a JSON `detail` list explaining the rejected input.

## How the Code Works

1. `TextData` extends Pydantic `BaseModel` and requires `text: str`.
	 `ConfigDict(extra="forbid")` rejects unexpected JSON fields.
2. `generate(text)` encodes the exact string as UTF-8, calculates SHA-256,
	 and returns a lowercase, 64-character hexadecimal digest.
3. `generate_from_query()` and `generate_checksum()` call that shared function
	 and wrap its output in a JSON `checksum` field.
4. `read_root()` returns a welcome message crediting GitHub Copilot.
5. `welcome_page()` serves [static/index.html](static/index.html) with
	 `FileResponse`. `StaticFiles` exposes assets under `/static`, resolving their
	 directory relative to the Python module rather than the shell's working directory.

The HTML page links to Swagger UI so users can submit requests interactively.
Its stylesheet is [static/style.css](static/style.css).

## Tests and Quality Checks

With the virtual environment active, run:

```bash
python -W error -m pytest -q
python -m pip check
git diff --check
```

The last two commands check installed dependency compatibility and whitespace
errors in tracked-file changes, respectively. The Git check requires Git.

The current suite in [test_main.py](test_main.py) contains 23 passing test cases.
It covers both HTTP methods, a known checksum, empty strings, whitespace,
Unicode, invalid bodies, missing input, both URL forms, welcome responses,
local HTML links, stylesheet serving, and API documentation.

`TestClient` runs the application in-process, so tests do not need a running
Uvicorn server. Redirect following is disabled to catch URL compatibility issues.

Warnings are promoted to errors with `-W error`. Pydantic's modern `ConfigDict`
avoids deprecated class-based configuration, and `httpx2` avoids the installed
Starlette version's deprecated `httpx` test-client fallback.

HTTP tests verify page and asset delivery, not browser rendering. The rocket's
SVG bounds were checked separately, but the responsive CSS changes have not
been visually verified in a browser across desktop and mobile viewports.

## Troubleshooting

| Problem | Suggested action |
| --- | --- |
| `ModuleNotFoundError` | Activate `.venv` and reinstall `requirements.txt` with the same Python interpreter. |
| `Could not import module "main"` | Run Uvicorn from the repository root. |
| `Address already in use` | Stop the process you started, or use `--port 8001` and update the browser URL. |
| Browser cannot reach the container | Forward the selected port through VS Code's Ports panel. |
| Welcome page appears unstyled | Open `/welcome` through Uvicorn, not the HTML file directly; check `/static/style.css` responds. |
| HTTP 422 | Check the `text` field, JSON syntax, string value, and absence of extra fields. |
| Tests report a deprecated `httpx` fallback | Install the repository's requirements into the interpreter running pytest. |

The `static` directory is required at application startup; keep it alongside
[main.py](main.py) when copying or deploying the project.

## Limitations and Deployment

This is a learning/demo application, not a complete production service.
Checksums are deterministic values for comparing text integrity; they are not
authentication tokens, encryption, or password hashes.

No authentication, rate limiting, input-size limits, database, or persistence
are implemented. GET requests put text in the URL, which may be recorded in
browser history and access logs; avoid using GET for sensitive text.

Before exposing the service publicly, add appropriate access controls,
request-size limits, HTTPS, monitoring, and deployment configuration. Omit
`--reload` when running outside development. No automated CI workflow or
container deployment files are currently included.

## Activity Work Completed

- Added a Pydantic request model and shared SHA-256 generator.
- Implemented and documented GET and JSON POST checksum routes.
- Added JSON and personalized HTML welcome experiences.
- Created HTTP tests and addressed the observed test-client warning.
- Fixed URL redirects, static serving, stylesheet links, and the page's API link.
- Adjusted SVG bounds and added narrow-layout, focus, and reduced-motion safeguards.
- Added Git exclusions for generated caches and virtual environments.
- Documented setup, Uvicorn execution, validation, testing, and current limitations.