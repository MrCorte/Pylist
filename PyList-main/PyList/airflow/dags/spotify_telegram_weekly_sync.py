from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime, timedelta
from telethon.sync import TelegramClient
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re


# Default arguments per il DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2026, 3, 24),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


def extract_spotify_links(text):
    if not text:
        return []
    return re.findall(r"https?://open\.spotify\.com/track/[a-zA-Z0-9]+", text)


def get_existing_track_ids(sp, playlist_id):
    existing_tracks = []
    results = sp.playlist_items(playlist_id)
    while results:
        for item in results["items"]:
            existing_tracks.append(item["track"]["id"])
        if results["next"]:
            results = sp.next(results)
        else:
            break
    return set(existing_tracks)


def sync_spotify_telegram():
    """Funzione principale che sincronizza Telegram con Spotify"""

    # Configurazione Spotify
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id="88a8cad4c7204938ac9cac6e0603e705",
        client_secret="4fd46690e17f47e18490e65ff00ad6b3",
        redirect_uri="http://127.0.0.1:8000",
        scope='playlist-modify-public'
    ))
    playlist_id = "0YqCQ1jfJ37VmIXWgPM90V"

    # Configurazione Telegram
    session_name = 'extractor'
    api_id = 21217655
    api_hash = 'a165366cecaebf5fbebd4368210fd3a2'
    chat_id = -1001592882608

    client = TelegramClient(session_name, api_id, api_hash)
    spotify_links = []

    with client:
        print("Connected to Telegram.")
        chat = client.get_entity(chat_id)
        for message in client.iter_messages(chat, limit=300):
            links = extract_spotify_links(message.text)
            spotify_links.extend(links)

    print(f"Found {len(spotify_links)} Spotify links.")

    # Estrai track IDs e filtra quelli nuovi
    track_ids = [link.split('/')[-1].split('?')[0] for link in spotify_links]
    existing_track_ids = get_existing_track_ids(sp, playlist_id)
    new_track_ids = [track_id for track_id in track_ids if track_id not in existing_track_ids]

    for track_id in new_track_ids:
        print(f"New track to add: {track_id}")

    # Aggiungi nuove tracce
    if new_track_ids:
        print(f"Adding {len(new_track_ids)} new tracks to the Spotify playlist...")
        try:
            sp.playlist_add_items(playlist_id, new_track_ids)
            print("Tracks added successfully!")
        except Exception as e:
            print(f"Errore durante l'aggiunta delle tracce: {e}")
            raise
    else:
        print("No new tracks to add.")


# Definizione del DAG
with DAG(
    'spotify_telegram_weekly_sync',
    default_args=default_args,
    description='Sincronizza tracce Spotify da Telegram ogni settimana',
    schedule='0 9 * * 1',  # Ogni lunedì alle 9:00
    catchup=False,
    tags=['spotify', 'telegram', 'sync'],
) as dag:

    sync_task = PythonOperator(
        task_id='sync_spotify_telegram',
        python_callable=sync_spotify_telegram,
    )
