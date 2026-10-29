# Upwork portfolio entry: OpsBoard

Paste these into Upwork → Profile → Portfolio → **Add project**. Upwork shows a character
counter on each field; check it as you paste, since limits can change.
Fill in the two `[ADD: …]` links once the demo is live and the repo is public.

## Project title
```
Operations Dashboard & Admin Panel: Next.js, FastAPI, PostgreSQL
```

## Your role
```
Full-stack developer (solo): UI, API, database, tests, deployment
```

## Project description
```
Demo project: a production-ready internal tool for orders, inventory and analytics, built to show how I work.

• Dashboard: KPIs vs the previous period, revenue trend, top products
• Orders: saved filters, CSV export, draft editor, status workflow that never oversells stock
• Viewer/manager/admin roles, audit log, rate-limited sign-in
• Fast on 100,000 orders: every API call under 200 ms (p95)
• 300+ automated tests, incl. WCAG 2.2 AA accessibility and phone layouts
• Docker deployment with HTTPS

Live demo: [ADD: live demo URL]
Code: [ADD: GitHub URL]
```

## Skills (pick the 5 Upwork allows, in this order)
Next.js · FastAPI · PostgreSQL · React · Docker
(Alternates if a field accepts more: TypeScript, Python, Tailwind CSS, REST API, Dashboard)

## Images (upload in this order; the first is the cover)
| File | Caption |
|---|---|
| `screenshots/dashboard-light.png` | Dashboard: revenue, orders, cancellation rate vs the previous period |
| `screenshots/orders-light.png` | Orders registry: search, status and date filters, sorting, CSV export |
| `screenshots/order-editor-light.png` | Draft editor: customer and product search, live total |
| `screenshots/order-detail-light.png` | Order workflow: confirm reserves stock, cancel releases it |
| `screenshots/mobile-light.png` | Works on phones: tables become cards, no sideways scrolling |
| `screenshots/dashboard-dark.png` | Dark mode |

All images are 1600×1200 (4:3). Regenerate them with `make run` and then `make screenshots`.

## Case-study text block (optional "Text" content block)
```
The problem
Operations teams often run on spreadsheets: no single view of sales, orders edited by two people at once, stock oversold, and nobody knows who changed what.

What I built
• A dashboard that compares every key figure with the previous period
• An orders registry that stays fast on 100,000 orders, with filters you can bookmark and share
• A draft → confirmed → shipped → delivered workflow. Confirming reserves stock atomically, so two people can't sell the last unit twice, and stale edits are rejected instead of silently overwritten
• Viewer/manager/admin roles enforced by the API, plus an audit log of every change

How it's built
Next.js 16, React 19, TypeScript and Tailwind on the front end. FastAPI, SQLAlchemy and PostgreSQL behind it. Docker Compose with a Caddy proxy and automatic HTTPS. GitHub Actions runs lint, 300+ tests (including browser and accessibility tests) and the production build on every push.
```

## Claims checklist (every number above is backed by the repo)
- 100,000 orders: `make seed` (docs/PROGRESS.md)
- p95 < 200 ms: measured, results in docs/PROGRESS.md
- 300+ tests: 244 API + 52 web + 10 browser = 306 (`make test`, `make e2e`)
- WCAG 2.2 AA, phones: axe checks and 320/412 px layout tests in `web/e2e/`
- Never oversells: `api/tests/test_concurrency.py` (parallel requests for the last unit)
