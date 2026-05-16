import os
from dotenv import load_dotenv
import re
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from youtube_converter import extract_youtube_tracks

load_dotenv()

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

def _get_sync_configs():
    configs = []
    i = 1
    while True:
        chat_id = os.getenv(f"SYNC_{i}_CHAT_ID")
        playlist_id = os.getenv(f"SYNC_{i}_PLAYLIST_ID")
        if not chat_id or not playlist_id:
            break
        configs.append((int(chat_id), playlist_id))
        i += 1
    if not configs:
        raise RuntimeError("No sync configs found. Set SYNC_1_CHAT_ID and SYNC_1_PLAYLIST_ID.")
    return configs

def _sync_one(client, sp, chat_id, playlist_id):
    print(f"  Chat: {chat_id} -> Playlist: {playlist_id}")
    chat = client.get_entity(chat_id)
    messages = list(client.iter_messages(chat, limit=300))

    spotify_links = []
    for message in messages:
        links = extract_spotify_links(message.text)
        spotify_links.extend(links)
    print(f"  Found {len(spotify_links)} Spotify links.")

    print("  Scanning for YouTube links...")
    yt_track_ids = extract_youtube_tracks(messages, sp)
    print(f"  Resolved {len(yt_track_ids)} tracks from YouTube links.")

    track_ids = [link.split("/")[-1].split("?")[0] for link in spotify_links]
    track_ids.extend(yt_track_ids)
    unique_track_ids = list(dict.fromkeys(track_ids))
    existing_track_ids = get_existing_track_ids(sp, playlist_id=playlist_id)
    new_track_ids = [t for t in unique_track_ids if t not in existing_track_ids]

    if new_track_ids:
        print(f"  Adding {len(new_track_ids)} new tracks...")
        for i in range(0, len(new_track_ids), 100):
            sp.playlist_add_items(playlist_id, new_track_ids[i:i+100])
        print("  Tracks added successfully!")
    else:
        print("  No new tracks to add.")

def sync_spotify_tracks():
    required = ["SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIFY_REFRESH_TOKEN",
                "TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_STRING_SESSION"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    print("Step 1: Initializing Spotify...")
    auth_manager = SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri="http://127.0.0.1:8000",
        scope="playlist-modify-public",
    )
    token_info = auth_manager.refresh_access_token(os.getenv("SPOTIFY_REFRESH_TOKEN"))
    sp = spotipy.Spotify(auth=token_info["access_token"])
    print("Step 1: Spotify OK")

    print("Step 2: Connecting to Telegram...")
    client = TelegramClient(
        StringSession(os.getenv("TELEGRAM_STRING_SESSION")),
        int(os.getenv("TELEGRAM_API_ID")),
        os.getenv("TELEGRAM_API_HASH"),
    )

    configs = _get_sync_configs()
    print(f"Step 2: {len(configs)} sync config(s) found.")

    with client:
        if not client.is_user_authorized():
            raise RuntimeError("Telegram session expired or invalid. Regenerate TELEGRAM_STRING_SESSION.")
        print("Step 2: Connected to Telegram.")

        for idx, (chat_id, playlist_id) in enumerate(configs, 1):
            print(f"\nStep 3.{idx}: Syncing config {idx}/{len(configs)}...")
            try:
                _sync_one(client, sp, chat_id, playlist_id)
            except Exception as e:
                print(f"  ERROR on config {idx}: {e}")

    print("\nAll syncs complete.")

if __name__ == "__main__":
    sync_spotify_tracks()
