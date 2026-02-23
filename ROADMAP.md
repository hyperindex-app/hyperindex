# HyperIndex Roadmap

This document outlines the planned evolution of HyperIndex from its current beta state toward a fully productionized service.

---

## Current Architecture (Beta)

- Static HTML dashboard served from a CDN (Vercel/Cloudflare Pages)
- Python generator runs locally on a schedule and pushes fresh JSON to GitHub
- GitHub acts as the data layer — Vercel serves the committed JSON files
- Simple and reliable, but couples data freshness to local machine uptime

---

## Phase 2 — Server-Side Data Pipeline

Move data generation off local machine onto a dedicated server or managed compute:

- Hosted Python cron (Railway, Render, or Fly.io) runs `generator.py` on schedule
- Data files written directly to server filesystem or object storage
- Dashboard fetches from a stable API endpoint rather than GitHub raw files
- Enables higher update frequency and removes dependency on local machine

---

## Phase 3 — Authentication & Subscriptions

- User accounts (sign up / log in)
- Tiered access: free preview vs. full data
- Payment integration for paid tier
- Server-side enforcement of access tiers (currently frontend-only gating)

---

## Phase 4 — Real-Time Data

- Sub-hourly update cadence for subscribers
- WebSocket or polling for live dashboard updates
- Alerts via Telegram / Discord / email on significant positioning changes

---

## Phase 5 — Platform Features

- Per-asset deep-dive pages
- Wallet-level transparency (optional pro feature)
- Multi-chain / multi-exchange expansion
- Public API for programmatic access

---

## Notes

- The current `data/` commit approach (Option A) is intentionally simple for beta.
  It will be replaced in Phase 2 with a proper server-side pipeline.
- Frontend auth gating is a placeholder — real access control requires Phase 3.
