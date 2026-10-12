# AskYourWallet — frontend

React + TypeScript + Vite client for AskYourWallet. It talks to the FastAPI backend over REST/JSON
and holds no business logic of its own: every figure on screen comes from an API response.

For the project as a whole — what it does, how the assistant stays grounded, how to run the
backend — see the [root README](../README.md).

## Running it

```bash
npm install
cp .env.example .env
npm run dev
```

<http://localhost:5173>. The backend needs to be up at whatever `VITE_API_URL` points to.

| Script | What it does |
|---|---|
| `npm run dev` | Vite dev server with HMR |
| `npm run build` | `tsc -b` then a production build into `dist/` |
| `npm run lint` | oxlint |
| `npm run preview` | Serve the built `dist/` locally |

TypeScript runs with `strict`, `verbatimModuleSyntax`, `erasableSyntaxOnly` and
`noUnusedLocals`/`noUnusedParameters`, so an unused import fails the build rather than warning.

## Configuration

One variable, in `.env` (see [`.env.example`](.env.example)):

```
VITE_API_URL=http://localhost:8000/api
```

Nothing else is configurable at build time and no key or secret belongs in this package — the Groq
API key lives only in the backend, which is the only thing that ever calls the model.

## Layout

Folders are organised by **feature**, not by file type: everything a screen needs sits together,
including its own `api.ts` data layer.

```
src/
  app/           App.tsx (routes), AppShell.tsx (sidebar + drawer), ThemeProvider.tsx
  features/
    auth/        Login, signup, AuthProvider, the auth context and token handling
    dashboard/   Summary cards, category donut, 6-month trend, recent activity
    transactions/Table, filters, create/edit dialog, CSV import dialog
    budgets/     Jar visualisation, summary, per-category tiles, edit dialog
    chat/        Transcript, answer renderer, tool trail, "Ask about this" links
    settings/    Account, appearance, data counts, assistant status, categories
  components/    Shared: Money, PageHeader, Logo, ThemeToggle, states (Spinner/Empty/Error)
    ui/          shadcn/ui primitives (button, card, dialog, select, table, …)
  hooks/         useApiQuery, useCategories, useDebouncedValue
  lib/           api client (axios + auth interceptor), format, types, categories→icons, cn
```

`useApiQuery(fetcher, deps)` returns `{ data, error, loading, refetch, setData }` and is the single
way a screen loads data; it keeps the fetcher in a ref so an inline arrow function does not restart
the request on every render.

Routes are lazy-loaded in `app/App.tsx` with a `Suspense` boundary around `AppShell`'s `<Outlet>`.
That matters because Recharts is large and only the dashboard uses it — the initial chunk stays
around 400 kB instead of 900 kB. Page components use **named** exports, hence the
`.then((m) => ({ default: m.XPage }))` in each `React.lazy` call.

## Design constraints

These are deliberate and worth preserving:

- **Every financial figure renders through `<Money>`** (or the `.figure` class), which applies
  JetBrains Mono with `tabular-nums` so columns of numbers line up. Amounts should never be plain
  spans.
- Dark-mode-first. Deep forest green primary, warm off-white light theme, one amber accent. Theme
  is a `dark` class on `<html>`, persisted to `localStorage` under `askyourwallet.theme`.
- Colours come from the HSL CSS variables in `index.css` via Tailwind tokens (`bg-card`,
  `text-muted-foreground`, …) — no raw hex in components.
- Budgets are **jar fills**, not horizontal progress bars.
- Category icons are literal objects from Lucide (cart, plug, plane). No robot, no sparkle, no
  "AI" glyph anywhere — including on the chat page.
- No gradients, no glassmorphism, no floating chat bubble. The chat composer is solid.
- `StrictMode` is on, so effects run twice in development; any send-once effect needs a ref guard
  (see the `?q=` deep link in `features/chat/ChatPage.tsx`).

## Backend contract notes

Details that shape the components:

- Money arrives as **strings** (Pydantic `Decimal` → JSON string). Parse before arithmetic.
- `percentage_used` and `savings_rate` are already percentages, not fractions.
- API routes carry **no trailing slash**.
- The canonical category list comes from `GET /api/categories`; `lib/categories.ts` maps its
  kebab-case icon names to Lucide components, so no picker hardcodes a list.
- A recurring budget has `month` and `year` set to `null`.
