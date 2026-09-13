#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

# Install project dependencies
pip install -r requirements.txt

# Collect static files for WhiteNoise
python manage.py collectstatic --no-input

# Run safe database migrations
python manage.py migrate

# Deterministically index RAG knowledge base
python manage.py ingest_knowledge
