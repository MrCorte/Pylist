# PyList

Automatically syncs Spotify tracks shared in a Telegram group chat to a Spotify playlist. Runs weekly via GitHub Actions.

## How it works

1. Connects to a Telegram group via Telethon
2. Scans the last 300 messages for Spotify track links
3. Compares against existing tracks in the target playlist
4. Adds only new (non-duplicate) tracks via the Spotipy API

## Project structure

```
runner.py                              # Main script (used by GitHub Actions)
main.py                                # Standalone script for local/ad-hoc use
airflow/dags/
  spotify_telegram_sync_d_a_g.py      # Primary Airflow DAG (env vars, runs Sundays)
  spotify_telegram_weekly_sync.py     # Legacy Airflow DAG (runs Mondays)
.github/workflows/pylist.yml          # GitHub Actions workflow (runs Wednesdays 19:00 UTC)
```

## Setup

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file (never commit this):

```env
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REFRESH_TOKEN=your_spotify_refresh_token
TELEGRAM_API_ID=your_telegram_api_id
TELEGRAM_API_HASH=your_telegram_api_hash
TELEGRAM_STRING_SESSION=your_telethon_string_session
```

#### Getting Spotify credentials
1. Create an app at [developer.spotify.com](https://developer.spotify.com)
2. Set redirect URI to `http://127.0.0.1:8000`
3. Run the OAuth flow once locally to obtain a refresh token

#### Getting Telegram credentials
1. Create an app at [my.telegram.org](https://my.telegram.org)
2. Generate a `StringSession` by running a Telethon script interactively once:

```python
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print(client.session.save())
```

### 3. Run locally

```bash
python runner.py
```

## GitHub Actions

The workflow runs automatically every Wednesday at 19:00 UTC and can also be triggered manually from the Actions tab.

Add the following secrets to your GitHub repository (`Settings → Secrets → Actions`):

| Secret | Description |
|--------|-------------|
| `SPOTIPY_CLIENT_ID` | Spotify app client ID |
| `SPOTIPY_CLIENT_SECRET` | Spotify app client secret |
| `SPOTIFY_REFRESH_TOKEN` | Spotify OAuth refresh token |
| `TELEGRAM_API_ID` | Telegram app API ID |
| `TELEGRAM_API_HASH` | Telegram app API hash |
| `TELEGRAM_STRING_SESSION` | Telethon StringSession string |

## Airflow (alternative)

```bash
airflow standalone
airflow dags trigger spotify_telegram_sync
```

Required env vars: `SPOTIPY_CLIENT_ID`, `SPOTIPY_CLIENT_SECRET`, `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`
