# StockAI

StockAI is a production-minded stock research platform built with the official Next.js
App Router and FastAPI as a hands-on learning project.
Version 0.1 deliberately proves one complete path—browser to Python API—before adding data
providers, accounts, databases, machine learning, containers, or cloud infrastructure.

## Repository map

```text
app/                 Next.js pages and styles
backend/app/         FastAPI application
backend/tests/       Python API tests
docs/                Architecture, roadmap, and learning notes
public/              Static web assets
```

## Run locally

Prerequisites: Node.js 22.13+ (LTS recommended), npm, and Python 3.12+.

### 1. Start the API

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` to explore FastAPI's generated API documentation.

### 2. Start the web app

In a second terminal:

```bash
cp .env.example .env.local
npm install
npm run dev
```

Commit the generated `package-lock.json` after the first successful install. The lockfile is
the reproducible record of the exact dependency tree and should change only with intentional
dependency updates.

Open the local URL printed by the web server. The market card changes to “API connected”
when both services are running.

## Verify

```bash
npm run build
cd backend && pytest
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Learning notes](docs/LEARNING.md)
- [Roadmap](docs/ROADMAP.md)
- [Changelog](CHANGELOG.md)

## Commit-style milestones

The work is organized into reviewable milestones; these are suggested commit messages, not
fabricated Git history:

1. `chore: scaffold StockAI web and API services`
2. `feat: connect dashboard to versioned market summary endpoint`
3. `test: add API health and response-contract coverage`
4. `docs: add v0.1 architecture, learning guide, roadmap, and changelog`
