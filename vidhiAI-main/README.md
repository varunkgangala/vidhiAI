# VidhiAI – Legal Compliance Assistant

An AI-powered Flask web application that analyses contracts for legal compliance, risk classification, and missing clauses using a RAG (Retrieval-Augmented Generation) pipeline.

## Features

- **Authentication** — Secure signup/login with SHA-256 hashed passwords
- **Multi-format input** — Upload PDF, DOCX, TXT or paste text directly
- **RAG Pipeline** — Retrieves applicable laws from cache → builds structured prompt → calls Claude API (with simulation fallback)
- **Risk Classification** — High / Medium / Low with per-section risk mapping
- **Compliance Scoring** — 0–100 score based on clause completeness, legality, clarity
- **Analysis History** — Persistent SQLite storage; per-user reports with full details
- **Professional UI** — Dark navy + gold legal theme with Playfair Display typography

## Quick Start

```bash
cd VidhiAI
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000` in your browser.

## Optional: Claude API

To use the real Claude API instead of simulation, set:

```bash
export ANTHROPIC_API_KEY=your_key_here
python app.py
```

## Project Structure

```
VidhiAI/
├── app.py               # Flask app, routes
├── auth/                # Login, signup, password hashing
├── rag/                 # Law fetcher, prompt builder, LLM engine
├── analysis/            # Contract parser, risk analyzer, compliance engine
├── database/            # SQLite models & helpers
├── templates/           # Jinja2 HTML templates
├── static/              # CSS + JS
└── data/                # Uploads + law cache
```

## Legal Disclaimer

VidhiAI is for informational purposes only and does not constitute legal advice. Always consult a qualified legal professional before acting on any analysis.
