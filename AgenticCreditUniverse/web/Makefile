ROOT := /Users/kim-youngbyeok/AgenticCreditUniverse/AgenticCreditUniverse
PY   := $(ROOT)/.venv/bin/python
UVI  := $(ROOT)/.venv/bin/uvicorn

.PHONY: backend frontend index install help

help:
	@echo "Targets: backend (FastAPI :8787) | frontend (Next :3000) | index (rebuild SQLite)"

backend:
	cd backend && $(UVI) app.main:app --reload --port 8787

frontend:
	cd frontend && npm run dev -- --port 3000

index:
	$(PY) backend/scripts/build_index.py

install:
	$(ROOT)/.venv/bin/pip install python-multipart itsdangerous pydantic-settings
	cd frontend && npm install
