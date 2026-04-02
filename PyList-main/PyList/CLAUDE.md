# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PyList is a pipeline that reads Spotify track links shared in a Telegram group chat and adds new (non-duplicate) tracks to a Spotify playlist. It is orchestrated via Apache Airflow.

## Setup

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Required environment variables for the Airflow DAG:
- `SPOTIPY_CLIENT_ID`
- `SPOTIPY_CLIENT_SECRET`
- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`

The Telethon session file (`extractor.session`) must exist and be authenticated before the DAG can run. Generate it by running a Telethon script interactively once with valid credentials.

## Running

**Airflow (scheduled pipeline):**
```bash
# Start Airflow standalone
airflow standalone

# Trigger the DAG manually
airflow dags trigger spotify_telegram_sync
```

**Standalone script (ad-hoc):**
```bash
python main.py
```

## Architecture

The core logic is the same across all files:
1. Connect to Telegram via Telethon and iterate the last 300 messages from a target group chat
2. Extract Spotify track URLs via regex (`open.spotify.com/track/...`)
3. Compare against existing playlist tracks via the Spotipy API
4. Add only new (non-duplicate) track IDs to the playlist

**DAG files in `airflow/dags/`:**
- `spotify_telegram_sync_d_a_g.py` — **primary DAG**, uses env vars for credentials, runs weekly on Sundays at midnight (`0 0 * * 0`)
- `spotify_telegram_weekly_sync.py` — older DAG with hardcoded credentials, runs Mondays at 9:00 — consider migrating to env vars

`main.py` and `bk.txt` are standalone versions of the script with hardcoded credentials — these are for manual/ad-hoc use and should not be the source of truth going forward.

## Credential Handling

`main.py`, `bk.txt`, and `spotify_telegram_weekly_sync.py` contain hardcoded API keys and session details. The preferred pattern is `spotify_telegram_sync_d_a_g.py`, which reads all secrets from environment variables via `os.getenv()`.