# v0.1 learning notes

## Technologies introduced

- **Next.js App Router** is the official React framework runtime used for routing,
  rendering, development, and production builds.
- **React** renders the page from components and updates it when API data arrives.
- **TypeScript** describes the expected JSON shape so mistakes are caught during development.
- **FastAPI** exposes Python functions as HTTP endpoints and generates interactive API docs.
- **Pydantic** validates and documents the backend response contract.
- **CORS** explicitly allows the local web origin to call the local API, which browsers otherwise block.
- **Semantic versioning** uses `major.minor.patch`: breaking change, compatible feature, compatible fix.

## The request path

1. React mounts the dashboard and sends `GET /api/v1/market-summary`.
2. FastAPI runs `get_market_summary` and validates the result with `MarketSummary`.
3. The browser decodes the JSON and React updates the quote card.
4. If the API is unavailable, the page shows an intentional setup message rather than fabricated data.

## Why the price is static

Real-time prices introduce provider selection, API keys, quotas, caching, market-hours semantics,
and licensing. Static deterministic data proves our architecture and tests first. Choosing a provider
is a product and data-quality decision for the next milestone—not a missing line of code.
