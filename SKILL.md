---
name: korea-domestic-flights
description: Search Korean domestic flights using a Playwright-based scraper adapted from a local flight search repository. Use when the user wants domestic airfare lookup, lowest-price comparisons, one-way or round-trip searches, route/date checks, or quick fare summaries for routes like 김포-제주, 부산-제주, 청주-제주. Prefer this skill for Korean domestic flight queries when local scraping is available.
---

# Korea Domestic Flights

Use this skill for **Korean domestic airfare searches** backed by the local Playwright project clone.

## What this skill currently supports

- One-way domestic flight search
- Round-trip domestic flight search
- Lowest-price summary
- Human-readable fare briefing
- Top results table in JSON

## Current implementation status

This is a **minimum viable wrapper** around the existing repository:

- Source repo clone expected at `tmp/Scraping-flight-information`
- Main entry point used: `scraping.searcher.FlightSearcher`
- Current scope: domestic route search only
- Not yet extended to date-range search, multi-destination, or alerts

## How to use

Run the wrapper script:

```bash
python skills/korea-domestic-flights/scripts/search_domestic.py --origin GMP --destination CJU --departure 2026-03-25
```

Round trip:

```bash
python skills/korea-domestic-flights/scripts/search_domestic.py --origin GMP --destination CJU --departure 2026-03-25 --return-date 2026-03-28
```

Options:
- `--origin`: IATA-like Korean airport code (e.g. GMP, CJU, PUS, TAE, CJJ)
- `--destination`: destination code
- `--departure`: departure date `YYYY-MM-DD`
- `--return-date`: optional return date for round trip
- `--adults`: default `1`
- `--cabin`: `ECONOMY|BUSINESS|FIRST` (default `ECONOMY`)
- `--max-results`: default `20`
- `--human`: print a short human-friendly summary instead of full JSON

## Notes

- This skill depends on the local cloned repository and its Python dependencies.
- If Playwright browsers are missing, install them in the source repo environment.
- If the target site changes its DOM, scraper maintenance may be required.
- If search returns empty, try rerunning or checking whether the provider site layout changed.

## Future expansion

Add later if needed:
- date-range cheapest-day search
- multi-destination comparison
- summarized human-readable fare briefing
- booking-link focused output
