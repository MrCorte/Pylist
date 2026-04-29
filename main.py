from telethon.sync import TelegramClient
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re
import os


sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri="http://127.0.0.1:8000",
    scope='playlist-modify-public'
))
playlist_id = os.getenv("SPOTIFY_PLAYLIST_ID", "0YqCQ1jfJ37VmIXWgPM90V")
chat_id = int(os.getenv("TELEGRAM_CHAT_ID", "-1001592882608"))


# --- FUNCTIONS ---
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

# --- MAIN SCRIPT ---
session_name = 'extractor'
api_id = int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH")
client = TelegramClient(session_name, api_id, api_hash)
spotify_links = []

with client:
    print("Connected to Telegram.")
    chat = client.get_entity(chat_id)
    for message in client.iter_messages(chat, limit=300):
        links = extract_spotify_links(message.text)
        spotify_links.extend(links)

print(f"Found {len(spotify_links)} Spotify links.")


track_ids = [link.split('/')[-1].split('?')[0] for link in spotify_links]  # rimuove eventuali parametri
existing_track_ids = get_existing_track_ids(sp, playlist_id)
new_track_ids = [track_id for track_id in track_ids if track_id not in existing_track_ids]

for track_id in new_track_ids:
    print(f"New track to add: {track_id}")

if new_track_ids:
    print(f"Adding {len(new_track_ids)} new tracks to the Spotify playlist...")
    try:
        sp.playlist_add_items(playlist_id, new_track_ids)
        print("Tracks added successfully!")
    except Exception as e:
        print(f"Errore durante l'aggiunta delle tracce: {e}")
else:
    print("No new tracks to add.")
