# Prudently

Agent-monitored hospital operations fleet for the **All Things Agentic Hackathon**
(Fortified Enterprise Fleet track). A Coordinator agent routes through an Agent Gateway to
three specialist agents — Shift Allocation, Supply Chain Resiliency, and Chaos & Continuity —
demoed against a scripted flu-outbreak surge at a single hospital.

**Status:** Day 1 complete (GCP project provisioned, capabilities probed, region locked).
See `AGENTS.md` for the architecture/agent roster, `docs/build-plan.md` for the full build
plan, and `docs/day1-probe-results.md` for which platform capabilities are real GCP products
vs. local-emulated fallbacks. Spin-up instructions, architecture diagram, and demo video link
will land here as the build progresses (target: complete by Aug 31, 2026).

## Repo layout

- `apps/api` — FastAPI + ADK backend (agents, platform adapters, routes)
- `apps/web` — Next.js dashboard
- `packages/datagen` — synthetic hospital data generator (roster, inventory, admissions)
- `infra/terraform` — GCP infrastructure as code
- `docs` — architecture diagram, Day-1 capability probe results, demo script

## Quickstart (once Day 1+ lands)

```
make probe      # verify which GCP capabilities are available in your project
make tf-apply   # provision infra
make seed       # generate synthetic hospital data
make dev        # run api + web locally
make deploy     # deploy both Cloud Run services
```
