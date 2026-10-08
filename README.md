# Campus Customs

A Yale-affiliated college merch storefront built for Homework 4 — a React + FastAPI shop
with a PydanticAI-powered chatbot that answers product, price, and stock questions
grounded in a real SQLite catalogue/inventory database, remembers logged-in shoppers'
chat history, and can search and recommend products live on the page.

See `output/harness.md` for how the whole system works (models, tools, safety rules,
specs), `output/design.md` for the front-end design decisions, and `output/usability.md`
for the usability features added in this build.

## 1. Get the data pack

The product catalogue, inventory, and product photos aren't committed to this repo
(`data/` is gitignored — it's large, and regenerable from the data pack you were given
for this assignment).

1. Get `data.zip` (provided separately for this assignment) and place it in this
   project's root folder (next to this README).
2. Unzip it so the result is:
   ```
   data/campus_customs.db
   data/products/*.jpg
   ```
   On Windows, right-click `data.zip` → "Extract All..." and extract here. On
   macOS/Linux: `unzip data.zip -d .` from this folder. If the zip contains its own
   top-level `data/` folder, make sure you don't end up with a nested `data/data/` —
   flatten it so `campus_customs.db` sits directly at `data/campus_customs.db`.

## 2. Set up your `.env`

1. Copy `.env.example` to `.env` in this same root folder:
   ```
   cp .env.example .env        # macOS/Linux
   copy .env.example .env      # Windows
   ```
2. Open `.env` and set `PORTKEY_API_KEY` to a real Portkey API key (get one at
   https://portkey.ai). Leave `MODEL_NAME` as-is unless you want to swap models.
3. `SESSION_SECRET_KEY` doesn't need to be set by hand — the backend generates one into
   `.env` automatically the first time it runs, if it's missing.

`.env` is gitignored — never commit it.

## 3. Backend — install and run

From this project's root folder:

```bash
python -m venv .venv
```

Activate it:
```bash
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS/Linux
```

Install dependencies, then run the server **from this project's root folder** (not from
inside `backend/` — the backend's modules import each other with package-relative
imports, e.g. `from . import db`, which only resolve correctly when Python loads it as
the `backend` package from one level up):

```bash
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

This creates the `chat_messages` table automatically on first run if it doesn't already
exist in `data/campus_customs.db` (it won't touch `users`, `catalogue`, or `inventory`).
The API is now at `http://localhost:8000` (try `http://localhost:8000/api/products`).

## 4. Frontend — install and run

In a separate terminal, from the `frontend/` folder:

```bash
cd frontend
npm install
npm run dev
```

## 5. Open the site

Open **http://localhost:5174** in your browser. The frontend's dev server proxies
`/api/*` requests to the backend on port 8000 automatically (see
`frontend/vite.config.ts`) — just make sure both servers from steps 3 and 4 are running
first.

A seed account exists for testing: `test@campuscustoms.yale.edu` / `password`. You can
also create a new account from the site itself.
