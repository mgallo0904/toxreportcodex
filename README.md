# Toxicology Review Agent

This repository contains the source code for a non‑clinical toxicology review assistant.

The application is organised as a mono‑repo with two primary submodules:

* `backend/` – a Python/FastAPI service responsible for ingesting files, performing
  structural mapping and deep review using AI models, storing persistent state in
  PostgreSQL, and exposing a REST API to the frontend.
* `frontend/` – a React application built with Vite that provides the user
  interface for uploading study packages, monitoring processing progress and
  reviewing the generated findings.

This project is designed to run on Render.com with a managed PostgreSQL database
and Redis instance. Configuration is supplied via environment variables (see
`backend/config.py` for details) and the deployment specification in
`render.yaml`.

The build instructions, architecture and phased implementation plan are defined
in the accompanying specification document. Phase 1 of the build sets up the
basic project structure, configuration classes, a health check endpoint and a
minimal React application. Later phases will incrementally add file ingestion,
background processing, rich UI components and fine‑tuning capabilities.