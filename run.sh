#!/bin/bash
poetry run python3 init_db.py
poetry run gunicorn --bind localhost:6277 server:app -w 1
