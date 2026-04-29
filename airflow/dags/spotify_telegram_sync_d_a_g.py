from airflow.providers.standard.operators.python import PythonOperator
from airflow import DAG
from datetime import datetime, timedelta
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from telethon.sync import TelegramClient
import re

# --- CONFIGURATION ---
TARGET_PLAYLIST_ID = "0YqCQ1jfJ37VmIXWgPM90V"
CHAT_ID = -1001592882608
TELEGRAM_SESSION_FILE = os.path.join(os.path.dirname(__file__), "../../extractor")

# --- HELPER FUNCTIONS ---
def extract_spotify_links(text):
    if not text:
        return []
    return re.findall(r"https?://open\.spotify\.com/track/[a-zA-Z0-9]+", text)

def get_existing_track_ids(sp, playlist_id):
    existing_tracks = set()
    results = sp.playlist_items(playlist_id)
    while results:
        for item in results["items"]:
            track = item.get("track")
            if track and track.get("id"):
                existing_tracks.add(track["id"])
        if results["next"]:
            results = sp.next(results)
        else:
            break
    return existing_tracks

# --- MAIN TASK ---
def sync_spotify_tracks():
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.environ["SPOTIPY_CLIENT_ID"],
        client_secret=os.environ["SPOTIPY_CLIENT_SECRET"],
        redirect_uri="http://127.0.0.1:8000",
        scope="playlist-modify-public"
    ))

    client = TelegramClient(
        TELEGRAM_SESSION_FILE,
        int(os.environ["TELEGRAM_API_ID"]),
        os.environ["TELEGRAM_API_HASH"],
    )

    try:
        with client:
            print("Connected to Telegram.")
            chat = client.get_entity(CHAT_ID)

            spotify_links = []
            for message in client.iter_messages(chat, limit=300):
                links = extract_spotify_links(message.text)
                spotify_links.extend(links)

            print(f"Found {len(spotify_links)} Spotify links.")

            track_ids = [link.split("/")[-1].split("?")[0] for link in spotify_links]
            unique_track_ids = list(dict.fromkeys(track_ids))
            existing_track_ids = get_existing_track_ids(sp, TARGET_PLAYLIST_ID)
            new_track_ids = [track_id for track_id in unique_track_ids if track_id not in existing_track_ids]

            if new_track_ids:
                print(f"Adding {len(new_track_ids)} new tracks to the Spotify playlist...")
                for i in range(0, len(new_track_ids), 100):
                    sp.playlist_add_items(TARGET_PLAYLIST_ID, new_track_ids[i:i+100])
                print("Tracks added successfully!")
            else:
                print("No new tracks to add.")

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise

# --- DAG DEFINITION ---
default_args = {
    "owner": "airflow",
    "start_date": datetime(2026, 3, 13),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5)
}

with DAG(
    "spotify_telegram_sync",
    default_args=default_args,
    schedule="0 19 * * 3",
    catchup=False,
    tags=["spotify", "telegram"]
) as dag:

    sync_task = PythonOperator(
        task_id="sync_spotify_tracks",
        python_callable=sync_spotify_tracks,
        doc_md="""
    ## Sync Spotify Tracks from Telegram
    This task extracts Spotify track links from a Telegram group chat and adds them to a Spotify playlist.
    It filters out tracks that already exist in the playlist.
    """
    )