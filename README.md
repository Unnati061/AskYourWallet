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

Transactions preserve explicit user categories, then use keyword rules, a selective offline
trained classifier, and finally the optional LLM. Uncertain offline predictions abstain.
CSV import uses rules and the local classifier without per-row network calls; unresolved
expenses become `Other`. Unmatched income is categorised as `Income` and bypasses the model.
See [model training and evaluation](backend/ml/README.md) for measured coverage and limitations.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19 · TypeScript · Vite · Tailwind CSS · shadcn/ui · Recharts |
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2 (async) · Alembic |
| Database | SQLite out of the box; PostgreSQL (Supabase / Neon free tier) by changing one env var |
| Auth | JWT — `python-jose` + `passlib`, tokens issued by the API itself |
| AI | Groq free tier (`openai/gpt-oss-120b`) with tool-use / function calling |
| Transaction model | TF-IDF + Logistic Regression trained with scikit-learn; offline JSON/NumPy inference |
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

Tests cover auth and token handling, transaction CRUD and CSV import, the rules engine and its
LLM fallback, budget/dashboard aggregation, and the chat tool-use loop (against a mocked provider, so
the suite needs no API key and makes no network calls). Additional model tests cover abstention,
precedence, offline import, and real predictions through create/edit/import API endpoints.

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

## Trained transaction categorisation model

The integrated classifier uses **TF-IDF word unigrams and bigrams with balanced Logistic
Regression** to categorise expense descriptions. It runs locally in the backend during manual
transaction creation, description edits, and CSV import. It needs no API key and does not require
payment mode, subcategory, amount, or date as model inputs.

### Dataset and training

Training uses the [Daily Transactions Dataset by prasad22 on Kaggle](https://www.kaggle.com/datasets/prasad22/daily-transactions-dataset).
After duplicate removal and filtering to expenses with at least 15 examples per source category,
2,127 of the original 2,461 records remain across 16 labels. Missing notes become empty text.
The stratified split uses 1,275 training, 426 validation, and 426 held-out test records with
`random_state=42`. The text encoder and classifier are fitted only on the training records;
the validation set selects the acceptance threshold without using test labels.

The shipped artifact contains vocabulary, IDF values, coefficients, and intercepts as numeric JSON.
The API uses NumPy for inference, so running the app requires neither pickle loading nor additional
scikit-learn/SciPy dependencies. Training dependencies are separate from runtime dependencies.

### Integration and fallback behaviour

The classification order is **explicit user category → keyword rules → local model → optional
LLM fallback**. Only expenses reach the model. CSV import uses rules and local inference without
per-row LLM requests; unresolved expenses become `Other`.

Model predictions are accepted only when their confidence is at least **0.50** and their source
label maps unambiguously to an app category. Supported mappings include Transportation → Transport,
Health → Healthcare, Apparel → Shopping, and Beauty → Personal Care. Broad labels such as Food
and Household abstain because they span multiple app categories. Blank text, unseen vocabulary,
and uncertain predictions also abstain. Existing records are not automatically reclassified.

### Evaluation results

| Held-out test measurement | Result |
|---|---:|
| Accuracy before confidence/category filtering | 67.37% |
| Macro F1 before filtering | 0.538 |
| Predictions accepted by the model | 59 of 426 (13.85% coverage) |
| Correct accepted predictions | 58 of 59 (98.31% accepted accuracy) |

**98.31% applies only to accepted predictions, not all transactions.** Coverage is measured before
the app's keyword rules; the model's additional coverage after rules may be lower. These results
come from one household's records with a random split, which can share merchant patterns across
splits. Performance on independent bank statements has not yet been measured, and model confidence
is not a calibrated guarantee of correctness.

The originally supplied model achieved a reproduced 93.19% accuracy using additional fields,
including human-entered subcategory text. With subcategory and payment mode unavailable, its
accuracy fell to 51.64%. The app therefore uses the retrained text-only classifier with abstention.

Examples when no category is selected: `hair cut` → Personal Care; `mobile recharge` → Subscriptions.
Set `ML_CATEGORIZATION_ENABLED=false` in `backend/.env` to disable the local classifier. Missing
or unreadable artifacts fall back to the existing categorisation path without blocking writes.

See the [model documentation](backend/ml/README.md) for all category mappings and retraining
commands, the [training script](backend/ml/train.py), and the [evaluation results](backend/ml/evaluation.json)
for the dataset checksum, threshold selection, and per-category metrics.

## Project structure

```
backend/
  app/
    routers/        # One module per domain: auth, transactions, budgets, dashboard, chat, categories
    models/         # SQLAlchemy ORM models + the canonical category list
    schemas/        # Pydantic request/response contracts
    services/       # Business logic, incl. categorization/{rules,ml,llm}.py
    tools/          # Groq tool definitions and the executor that runs them against the DB
  alembic/          # Migrations
  ml/               # Trained JSON artifact, training script, evaluation results and documentation
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
