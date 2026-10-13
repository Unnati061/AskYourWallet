# AskYourWallet

A personal finance assistant you can talk to. It imports your bank statements, categorises the
transactions, tracks per-category budgets, and answers questions about your money in plain
English — with every figure looked up in your own ledger before it is quoted.

The chat assistant never reports a number it did not fetch from the database. That constraint is
enforced in the backend (see [Grounding](#how-the-assistant-stays-grounded)), and surfaced in the
UI as a per-answer trail of the lookups that produced it.

## Screens

| Screen | What it does |
|---|---|
| **Dashboard** | Month summary, spending by category, 6-month income/expense trend, recent activity |
| **Transactions** | Filterable table, create/edit/delete, CSV bank-statement import with a per-row report |
| **Budgets** | Per-category monthly limits as jar fills, over-budget flagging, recurring or single-month scope |
| **Chat** | Natural-language Q&A over your data, with the tool trail behind each answer |
| **Settings** | Account, theme, assistant availability, the canonical category list |

Transactions are categorised by a keyword rules engine first; only what the rules cannot place
falls through to the LLM, and anything still unresolved lands in `Other`.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19 · TypeScript · Vite · Tailwind CSS · shadcn/ui · Recharts |
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2 (async) · Alembic |
| Database | SQLite out of the box; PostgreSQL (Supabase / Neon free tier) by changing one env var |
| Auth | JWT — `python-jose` + `passlib`, tokens issued by the API itself |
| AI | Groq free tier (`openai/gpt-oss-120b`) with tool-use / function calling |
| CSV import | pandas |

Everything runs on free tiers. No paid API is required, and the app is fully usable with no AI key
at all — only the chat page needs one.

## Local development (Windows and VS Code)

Open this folder in VS Code. You need Python 3.12 and Node.js 22 or newer installed once.
The project uses SQLite locally, so PostgreSQL is not required. Backend settings and the
frontend API URL are already configured for local development in the example env files.

### One-time setup for a fresh checkout

Open a VS Code PowerShell terminal at the project root and run:

```powershell
py -3.12 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if (-not (Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
```

For a fresh `backend\.env`, replace the example `JWT_SECRET_KEY` with a generated development
secret. This command prints one; paste its output into `backend\.env`:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

`DATABASE_URL` in the example already selects SQLite. `GROQ_API_KEY` is optional; without one,
signup, transactions, CSV import, budgets and the dashboard work normally, while live AI chat is
disabled with an explanation. Install frontend packages once:

```powershell
npm --prefix frontend install
```

### Start the app

Open **two VS Code terminals** at the project root and run exactly one command in each.

**Terminal 1 — backend:**

```powershell
.\backend\run-dev.cmd
```

This applies pending migrations, seeds the demo account only when creating a brand-new local
database, then starts the API. Existing SQLite data is preserved across restarts.

**Terminal 2 — frontend:**

```powershell
npm --prefix frontend run dev
```

Open <http://localhost:5173>. API documentation is at <http://localhost:8000/docs>. Demo sign-in
(created automatically only for a new database): `demo@askyourwallet.app` / `demo12345`.

To use PostgreSQL instead, set `DATABASE_URL` in `backend\.env` to a PostgreSQL async driver URL.
The frontend's `VITE_API_URL` defaults to `http://localhost:8000/api`.

## Configuration

All configuration is environment-based; nothing is hardcoded and no secret is committed. See
[`backend/.env.example`](backend/.env.example) for the annotated list — it covers the database URL,
JWT signing secret and lifetime, the Groq key and models, the tool-loop safety valve, and the CORS
origin. The frontend's single variable lives in [`frontend/.env.example`](frontend/.env.example).

## Tests

```powershell
.\backend\.venv\Scripts\python.exe -m pytest -c backend\pytest.ini
```

64 tests covering auth and token handling, transaction CRUD and CSV import, the rules engine and its
LLM fallback, budget/dashboard aggregation, and the chat tool-use loop (against a mocked provider, so
the suite needs no API key and makes no network calls).

Frontend checks:

```powershell
npm --prefix frontend run lint
npm --prefix frontend run build
```

## How the assistant stays grounded

`POST /api/chat` sends the question, a capped slice of history, and four read-only tool definitions
to Groq. If the model asks for a tool, the **backend** runs the corresponding query against the
signed-in user's rows and feeds the result back; the model only ever sees data the API chose to
return. The loop repeats until it produces prose, bounded by `GROQ_MAX_TOOL_ROUNDS`.

The tools are `get_transactions`, `get_spending_by_category`, `get_budget_status` and
`get_monthly_trend`. Two safeguards sit on top:

- `user_id` is bound from the authenticated request, never from model output, so a hallucinated id
  cannot reach another account's data.
- If a question looks like it is about actual figures and the model tried to answer without calling
  anything, the request is retried once with tool use forced.

The response carries the tool calls that ran, plus a `grounded` flag, and the UI shows both — an
answer with no lookup behind it is labelled as such instead of being presented as fact.

## Project structure

```
backend/
  app/
    routers/        # One module per domain: auth, transactions, budgets, dashboard, chat, categories
    models/         # SQLAlchemy ORM models + the canonical category list
    schemas/        # Pydantic request/response contracts
    services/       # Business logic, incl. categorization/{rules,llm}.py kept deliberately separate
    tools/          # Groq tool definitions and the executor that runs them against the DB
  alembic/          # Migrations
  tests/
  seed.py           # Demo dataset
frontend/
  src/
    features/       # Feature-first: auth, transactions, budgets, dashboard, chat, settings
    components/     # Shared UI (Money, PageHeader, states) + components/ui primitives
    hooks/          # useApiQuery, useCategories, useDebouncedValue
    lib/            # API client, formatters, types, category→icon map
    app/            # Routing, shell, theme
```

Routes are code-split, so the Recharts-heavy dashboard is not in the initial bundle.

## Design notes

Dark-mode-first, deep forest green with a single amber accent on a warm off-white light theme. Inter
for the interface; **JetBrains Mono with tabular numerals for every financial figure**, which is why
all amounts render through one `Money` component rather than ad-hoc spans. Category icons are
literal objects — a cart, a plug, a plane. Budgets are jar fills rather than progress bars, and
there is no gradient, no glassmorphism and no "AI" glyph anywhere.

## Deployment

The repository is ready for a Vercel frontend and Render API deployment. The included
[`render.yaml`](render.yaml) creates the FastAPI service, a managed PostgreSQL database, runs
migrations before each deployment, and generates the production JWT signing secret. It converts
Render's standard PostgreSQL connection string to the async driver URL the application requires.

1. In Render, choose **New +** → **Blueprint**, select this GitHub repository and its `main`
   branch, then apply the detected `render.yaml`. Copy the API's public URL after deployment.
   Enter `GROQ_API_KEY` only if you want live AI chat; all other features work without it.
2. In Vercel, import this GitHub repository and set its root directory to `frontend`. Add
   `VITE_API_URL` with the value `https://YOUR-RENDER-API.onrender.com/api`, then deploy. The
   checked-in `frontend/vercel.json` preserves React routes
   on direct links.
3. In Render's environment settings, add `FRONTEND_URL` with the exact Vercel deployment origin,
   such as `https://askyourwallet.vercel.app`, then redeploy the API. This enables browser CORS
   access only from the deployed UI.

Do not commit `.env` files or paste the Groq key into repository settings. The production database
is intentionally separate from the local SQLite database.

## Not in scope

Receipt OCR, live bank connections, multi-currency, investment tracking and automatic
recurring-transaction detection are all deliberately out of the MVP.

## License

MIT
