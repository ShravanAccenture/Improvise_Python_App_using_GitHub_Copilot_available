# Text Checksum API: Technical Documentation

This document describes the implementation, API contracts, development workflow,
frontend, tests, and operational limitations of this repository. For a shorter
introduction and quick-start instructions, see [README.md](README.md).

## Contents

- [Project Scope](#project-scope)
- [Repository Layout](#repository-layout)
- [Architecture and Request Flow](#architecture-and-request-flow)
- [Environment and Dependencies](#environment-and-dependencies)
- [Installation and Execution](#installation-and-execution)
- [Backend Reference](#backend-reference)
- [API Reference](#api-reference)
- [Validation and Checksum Semantics](#validation-and-checksum-semantics)
- [Frontend Reference](#frontend-reference)
- [Testing and Verification](#testing-and-verification)
- [Corrections Made During the Activity](#corrections-made-during-the-activity)
- [Troubleshooting](#troubleshooting)
- [Security and Deployment](#security-and-deployment)
- [Maintenance Guide](#maintenance-guide)

## Project Scope

The project demonstrates how GitHub Copilot can support a FastAPI development
activity: creating a Pydantic model, sharing checksum-generation logic between
routes, documenting endpoints, adding tests, and addressing warnings.

The detailed activity requires a text checksum. Accordingly, each request returns
one SHA-256 checksum, not a list of generated language-model tokens. Although the
activity described an existing generator, the starting Python file was empty;
the generator and routes were implemented during this work.

The application also serves a static welcome page personalized for Chimmani
Venumuni. The JSON welcome message credits GitHub Copilot. The frontend and API
are delivered by the same server, but the frontend is a welcome page rather than
a custom text-input form. Its "Try it out" link opens the interactive API docs.

## Repository Layout

```text
copilot_lab/
|-- .gitignore
|-- README.md
|-- documentation.md
|-- main.py
|-- requirements.txt
|-- test_main.py
`-- static/
    |-- index.html
    `-- style.css
```

| File | Responsibility |
| --- | --- |
| [main.py](main.py) | FastAPI application, Pydantic model, checksum function, API routes, and static serving |
| [requirements.txt](requirements.txt) | Version ranges for application and testing dependencies |
| [test_main.py](test_main.py) | In-process HTTP regression tests |
| [static/index.html](static/index.html) | Personalized HTML welcome page and inline rocket illustration |
| [static/style.css](static/style.css) | Layout, colors, responsive constraints, animation, and accessibility styles |
| [.gitignore](.gitignore) | Excludes `.venv`, Python bytecode, and pytest caches |
| [README.md](README.md) | Project overview and quick-start guidance |
| [documentation.md](documentation.md) | Detailed technical reference |

The repository currently has no database, Dockerfile, dev-container configuration,
automated CI workflow, package build configuration, or dependency lockfile.
Generated cache directories are not part of the source tree.

## Architecture and Request Flow

```mermaid
flowchart TD
    Client[Browser or HTTP client] --> Server[Uvicorn ASGI server]
    Server --> App[FastAPI application]
    App --> Get[GET /generate: query validation]
    App --> Post[POST /generate: TextData validation]
    Get --> Generator[generate: UTF-8 and SHA-256]
    Post --> Generator
    Generator --> Result[JSON checksum response]
    App --> Welcome[GET /: JSON welcome]
    App --> Page[GET /welcome: FileResponse]
    App --> Assets[/static: StaticFiles]
    App --> Docs[Swagger UI, ReDoc, OpenAPI]
```

For POST requests, FastAPI parses the JSON body and validates it through
`TextData` before calling the route function. Invalid input produces HTTP 422
without reaching the checksum handler. GET requests validate their required
`text` query parameter separately; they do not use the JSON-body model.

Both checksum handlers call the same `generate()` function. They return Python
dictionaries, which FastAPI serializes as JSON. Route handlers are synchronous
`def` functions; FastAPI runs synchronous handlers in its worker thread pool.
No custom startup or shutdown hooks are implemented.

## Environment and Dependencies

The documented setup requires Python 3.11 or newer because the `httpx2` testing
dependency requires Python 3.11. Development and the recorded tests were performed
using Python 3.14.2 in a Linux VS Code dev container. Other Python versions have
not been certified by a multi-version test matrix.

| Dependency | Declared requirement | Purpose |
| --- | --- | --- |
| FastAPI | `>=0.119,<1` | ASGI application, routing, validation integration, and OpenAPI |
| Pydantic | `>=2.12,<3` | Request model and configuration |
| Uvicorn | `>=0.38,<1` | Web server |
| httpx2 | Unpinned | HTTP transport used by the installed Starlette TestClient |
| pytest | `>=9,<10` | Test execution and parameterization |

`hashlib`, `pathlib`, and the test suite's `html.parser` are Python standard-library
modules. Starlette is installed through FastAPI. All runtime and testing
dependencies currently share one requirements file.

Version ranges allow dependency updates; they do not guarantee identical installs.
The tested installation included FastAPI 0.162.0, Pydantic 2.14.2, Uvicorn 0.54.0,
httpx2 2.16.0, and pytest 9.2.0. These are observed versions, not additional pins.

## Installation and Execution

### Create an Environment

Open a terminal in the repository root. On Linux or macOS:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

If necessary, use `python3` for the environment-creation command. On Windows
PowerShell, activate with `.venv\Scripts\Activate.ps1` instead of `source`.
Using `python -m pip` helps keep package installation tied to the active interpreter.

No database connection, API key, or application-specific environment variables
are required.

### Start the Development Server

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

`main:app` means "import the `app` object from the `main` module." Run this command
from the repository root so the module is importable. The `static` directory must
remain alongside the module. Static paths resolve relative to the module, but
that does not remove Uvicorn's module-import requirement.

`--reload` watches for source changes and is for development only. `0.0.0.0` binds
all network interfaces, which supports container port forwarding. Outside a
container, `--host 127.0.0.1` restricts the binding to the local machine.

| Address | Use |
| --- | --- |
| http://localhost:8000/ | JSON welcome |
| http://localhost:8000/welcome | HTML welcome |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/openapi.json | Machine-readable OpenAPI schema |

In Codespaces or a remote dev container, forward port 8000 in VS Code's Ports
panel and use its forwarded address. Port visibility should remain private unless
public access is explicitly needed. Do not use `0.0.0.0` as the browser URL.

Stop the server with `Ctrl+C` in its terminal. Run `deactivate` when finished with
the virtual environment. If port 8000 is occupied, use `--port 8001` and update
the URLs in your browser and requests.

## Backend Reference

### Application and Static Directory

`app = FastAPI()` creates the ASGI application. It currently uses FastAPI's default
application metadata and documentation URLs.

`STATIC_DIR = Path(__file__).resolve().parent / "static"` calculates an absolute
path to the asset directory. `app.mount()` exposes that directory at `/static`
through `StaticFiles`. Missing the directory prevents normal application startup.
The mount exposes files present in that directory, so do not place secrets there.

### TextData Model

```python
class TextData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
```

`text` is required because it has no default. `extra="forbid"` rejects unexpected
fields. The model uses Pydantic v2 configuration rather than a deprecated inner
`Config` class. It does not define a maximum length or a nonempty-string constraint.

### generate Function

```python
def generate(text: str) -> str:
    """Generate a SHA-256 checksum from UTF-8 text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
```

This is the reusable domain function, not an HTTP route. It accepts a Python
string and returns only the digest. Request validation belongs to the HTTP
boundary; the function does not validate arbitrary non-string Python objects.

### Route Functions

| Function | Behavior |
| --- | --- |
| `read_root()` | Returns the JSON welcome message |
| `welcome_page()` | Returns `static/index.html` as `text/html` through `FileResponse` |
| `generate_from_query(text)` | Accepts validated query text and returns `{"checksum": generate(text)}` |
| `generate_checksum(data)` | Accepts `TextData` and returns `{"checksum": generate(data.text)}` |

Both checksum functions have slash and non-slash decorators. The non-slash
routes are canonical in OpenAPI; slash aliases use `include_in_schema=False`.
The HTML welcome route is also omitted from OpenAPI. These exclusions affect
documentation, not whether the routes can be requested.

## API Reference

### GET /

No parameters or body are required. Successful response: HTTP 200, JSON.

```json
{"message": "Welcome to the API! Developed by GitHub Copilot"}
```

### GET /generate

Required query parameter: `text`, a string. `/generate/` is an equivalent alias
and does not redirect.

```bash
curl --get http://localhost:8000/generate \
  --data-urlencode 'text=abc'
```

Successful response: HTTP 200, JSON.

```json
{"checksum": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"}
```

Use `--data-urlencode` for whitespace and special characters. Omitting `text`
returns HTTP 422. Supplying an empty query string value is valid. The GET route
does not apply the POST model's prohibition on extra JSON fields to query parameters.

### POST /generate

Send `Content-Type: application/json` with a JSON object containing exactly one
field, `text`. `/generate/` is an equivalent alias and does not redirect.

```bash
curl http://localhost:8000/generate \
  -H 'Content-Type: application/json' \
  -d '{"text": "abc"}'
```

Successful response: HTTP 200, JSON with the same checksum as the GET example.
There is no database write or stored token associated with this request.

### GET /welcome and Static Assets

`/welcome` returns the personalized HTML page with HTTP 200 and a `text/html`
content type. `/static/style.css` returns its stylesheet with a `text/css` content
type. Open the page through the application, not directly from the filesystem,
because its resource and navigation URLs are server-relative.

The mounted directory also makes `/static/index.html` available as a static file.
`/welcome` is the intended page entry point. The Markdown documentation is not
served by an application route; read it in the repository or VS Code preview.

### Documentation Endpoints

Swagger UI at `/docs` lets users submit a JSON body, execute requests, and inspect
responses. ReDoc at `/redoc` provides a reference view. `/openapi.json` contains
the generated schema, including the required `TextData` body and its prohibition
on additional properties. Route summaries and docstrings populate operation text.

The default documentation pages reference external frontend assets. The checksum
API itself does not require an external API, but browser documentation rendering
may require access to those asset hosts.

### HTTP Status Summary

| Status | Meaning |
| --- | --- |
| 200 | Valid checksum request, welcome response, or existing documentation/static resource |
| 422 | Missing or invalid required input, malformed JSON, or an invalid POST body |
| 404 | An unknown route or nonexistent static file |
| 405 | An unsupported HTTP method on an existing route |

Successful checksum responses contain a `checksum` field. Validation failures
contain a `detail` list. Exact validation messages are generated by FastAPI and
Pydantic and may change with dependency versions.

## Validation and Checksum Semantics

### POST Input Rules

| JSON body | Expected result |
| --- | --- |
| `{"text": "hello"}` | 200 |
| `{"text": ""}` | 200 |
| `{"text": "  hello\n"}` | 200; whitespace is included in the checksum |
| `{}` | 422; required text missing |
| `{"text": null}` | 422 |
| `{"text": 123}` or `{"text": true}` | 422 |
| `{"text": []}` or `{"text": {}}` | 422 |
| `{"text": "hello", "extra": true}` | 422; extra field forbidden |
| Missing body, invalid JSON, or a body that is not the required object | 422 |

Example validation request:

```bash
curl -i http://localhost:8000/generate \
  -H 'Content-Type: application/json' \
  -d '{"text": null}'
```

### Exact-Text Behavior

Input is encoded as UTF-8 without trimming, case folding, newline replacement,
or Unicode normalization. Thus `hello`, `Hello`, and `hello ` generally produce
different digests. Visually identical text represented by different Unicode
normalization forms may also produce different digests.

The output is always a lowercase hexadecimal SHA-256 digest of 64 characters
for successfully encoded input. Empty text has this well-known checksum:

```json
{"checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}
```

The server returns a checksum for comparison; it does not accept an expected
checksum or perform an integrity-verification workflow. SHA-256 is a one-way
hash, not encryption, an authentication credential, or a password-storage scheme.

## Frontend Reference

### HTML Structure

[static/index.html](static/index.html) includes a UTF-8 declaration, viewport
metadata, a page title, a main landmark, a personalized heading, an inline SVG
rocket, a displayed quotation, navigation links, and a project-information section.

The primary link points to `/docs`. The project-source link opens an external
GitHub URL in a new tab with `rel="noopener noreferrer"`. Its external destination
is not validated by the local HTTP tests. There is no custom frontend JavaScript,
form submission code, or client-side token generation.

The rocket uses SVG paths and gradients. Its `viewBox` is `0 0 220 144`, enlarged
to contain the translated and rotated flame. The SVG uses a title and accessible
image labeling. The background decoration is marked `aria-hidden="true"`.

### Styles and Responsive Behavior

[static/style.css](static/style.css) defines color variables, background layers,
the centered layout, typography, buttons, and illustration sizing. A media query
at 900px reduces layout padding and the rocket width.

`min-width: 0` and `overflow-wrap: anywhere` help the main panel accommodate
narrow layouts and long text. Button and rocket `max-width: 100%` constraints
keep those elements within their parent containers.

The rocket's floating animation lasts 4.2 seconds per cycle. A
`prefers-reduced-motion: reduce` query disables it, button transitions, and hover
movement. `:focus-visible` adds a visible outline for keyboard navigation.

The font stack names Space Grotesk followed by fallbacks, but the repository
does not bundle or load that font. Appearance therefore depends on fonts installed
on the user's system. Accessibility safeguards are implemented; a full accessibility
audit and desktop/mobile browser rendering checks have not been completed.

## Testing and Verification

### Commands

```bash
python -W error -m pytest -q
python -m pip check
git diff --check
```

`-W error` treats warnings as failures. `pip check` verifies installed dependency
compatibility. `git diff --check` checks whitespace in tracked changes; it is not
a complete source linter and does not validate all untracked files.

### Test Design

[test_main.py](test_main.py) creates a `TestClient` fixture inside a context
manager and disables automatic redirect following. Tests run the application
in-process, without a Uvicorn server or an external network connection.

| Test area | Number of cases | Evidence |
| --- | --- | --- |
| GET checksums | 4 | ASCII, empty text, whitespace, and Unicode |
| POST checksums | 4 | Same inputs and agreement with GET results |
| Known checksum | 1 | Hardcoded SHA-256 digest for `abc` |
| Slash aliases | 1 | Both methods succeed directly on `/generate/` |
| Invalid POST bodies | 7 | Missing, null, numeric, boolean, collection, and extra-field input |
| Missing POST body | 1 | HTTP 422 |
| Malformed JSON | 1 | HTTP 422 |
| Missing GET text | 1 | HTTP 422 |
| JSON welcome | 1 | HTTP 200 and GitHub Copilot credit |
| HTML and local links | 1 | HTML parsing, working local links, and CSS content type |
| API documentation | 1 | Docs availability and required JSON body in OpenAPI |
| Total | 23 | Current automated suite |

The recorded suite passes all 23 cases with warnings promoted to errors.
Dependency compatibility and editor diagnostics have also been checked. A live
Uvicorn smoke test returned the expected `abc` digest and HTTP 200 for `/welcome`.

The SVG flame's transformed coordinates were checked separately against its
viewBox. That was a focused geometry check, not a committed browser test.
The suite does not verify screenshots, overflow at every viewport, external links,
screen-reader behavior, load capacity, security controls, or every supported Python
version. Passing tests should not be interpreted as production certification.

## Corrections Made During the Activity

| Issue | Correction |
| --- | --- |
| Deprecated TestClient HTTP fallback | Installed and documented `httpx2` |
| Deprecated Pydantic configuration pattern | Used Pydantic v2 `ConfigDict` |
| Inconsistent route URLs and redirect-masked tests | Served both URL forms directly and disabled redirect following in tests |
| Unexpected POST fields accepted | Added `extra="forbid"` |
| Placeholder JSON welcome message | Replaced the placeholder with a GitHub Copilot credit |
| Static page unavailable | Mounted `/static` and added `/welcome` |
| Incorrect stylesheet filename | Linked to `/static/style.css` |
| Missing API link destination | Pointed "Try it out" to `/docs` |
| Rocket flame clipping | Increased SVG drawing bounds |
| Narrow-layout overflow risk | Added wrapping and maximum-width constraints |
| Missing focus and reduced-motion safeguards | Added keyboard outlines and motion overrides |
| Generated files appearing in Git status | Added cache and environment exclusions |
| Outdated documentation | Corrected model names, setup requirements, and route descriptions |

These are implemented changes, not claims that the project had every deprecated
configuration at the start. The original Python file was empty.

## Troubleshooting

| Symptom | Check or remedy |
| --- | --- |
| Python package cannot be imported | Activate the correct environment and run `python -m pip install -r requirements.txt`. |
| pip reports an incompatible Python version | Use Python 3.11 or newer for the documented dependency set. |
| Uvicorn cannot import `main` | Open the terminal in the repository root and use `main:app`. |
| Static directory missing at startup | Keep the complete `static` directory alongside the Python module. |
| Port already in use | Stop your existing server or select a different port; do not terminate unrelated processes. |
| Browser cannot connect from a dev container | Forward the chosen port and use the forwarded address. |
| Page is unstyled | Request `/static/style.css` through the same running server and avoid opening the HTML as a local file. |
| POST returns 422 | Check JSON syntax, the required string field, and the absence of extra fields. |
| Unexpected GET checksum | URL-encode input and check whitespace and Unicode representation. |
| TestClient emits an HTTP fallback warning | Install requirements into the same interpreter used by pytest. |
| Python edits do not appear in the server | Restart Uvicorn or use development `--reload`. |
| CSS edits do not appear in the browser | Reload the page and check for cached stylesheet content. |

Do not suppress warnings merely to obtain a passing test run. Identify their
source, make a compatible correction, and rerun the relevant tests.

## Security and Deployment

The application currently implements no authentication, authorization, rate
limiting, request-size limits, persistence, custom audit logging, or CORS policy.
It has no database and makes no application-specific outbound API calls.

GET inputs appear in URLs and may be recorded in browser history or access logs.
POST avoids placing text in the URL, but does not itself guarantee confidentiality;
use HTTPS and avoid logging sensitive bodies when deploying a service.

Unbounded input can consume memory and hashing time. Before public deployment,
add input and request-body limits, access controls, suitable concurrency settings,
monitoring, and abuse protection. Keep credentials out of the publicly served
static directory. Default browser docs may require external asset access.

An example server command without the development watcher is:

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Removing `--reload` alone does not make the service production-ready. A real
deployment should supply HTTPS termination, process supervision, dependency
locking, security review, and infrastructure configuration appropriate to its
environment. No container build files or deployment automation are included here.

## Maintenance Guide

1. Keep checksum behavior in `generate()` so the GET and POST routes remain consistent.
2. Update `TextData` and invalid-input tests together when changing the body contract.
3. Preserve both URL forms unless intentionally making a documented breaking change.
4. Update HTML resource links when changing asset filenames or serving paths.
5. Run warning-strict tests after code and dependency changes; run `pip check` after installs.
6. Update both this reference and the README when routes, setup requirements, or test coverage change.
7. Perform browser checks after layout changes, including keyboard navigation, reduced motion,
   narrow screens, enlarged text, and asset rendering.

Potential future work includes a custom checksum form, a locked dependency set,
CI and Python-version matrices, automated browser/accessibility tests, deployment
configuration, and security controls. These are recommendations, not current features.