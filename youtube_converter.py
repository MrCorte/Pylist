import re
import json
import urllib.request
import urllib.parse

_YT_PATTERNS = [
    r"https?://(?:www\.|m\.)?youtube\.com/watch\?[^\s]*v=([a-zA-Z0-9_-]{11})",
    r"https?://youtu\.be/([a-zA-Z0-9_-]{11})",
    r"https?://(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
]

_NOISE_PATTERNS = [
    r"\s*[\(\[][^\)\]]*(?:official|video|audio|lyrics?|hd|hq|mv|clip|visualizer|4k|music)[^\)\]]*[\)\]]",
    r"\s*\|.*$",
    r"\s*//.*$",
    r"\s*#\w+",
]

_OEMBED_URL = "https://www.youtube.com/oembed"


def _extract_yt_urls_with_ids(text):
    seen = set()
    for pattern in _YT_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            video_id = match.group(1)
            if video_id not in seen:
                seen.add(video_id)
                yield f"https://www.youtube.com/watch?v={video_id}", video_id


def _fetch_yt_title(video_url, timeout=5):
    params = urllib.parse.urlencode({"url": video_url, "format": "json"})
    try:
        with urllib.request.urlopen(f"{_OEMBED_URL}?{params}", timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            return data.get("title")
    except Exception:
        return None


def _parse_title(raw_title):
    cleaned = raw_title
    for pattern in _NOISE_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    if " - " in cleaned:
        parts = cleaned.split(" - ", maxsplit=1)
        artist = parts[0].strip()
        track = parts[1].strip()
        return artist, track
    return None, cleaned.strip()


def _is_confident_match(query, candidate, threshold=0.65):
    """Bidirectional token overlap: query tokens in candidate AND candidate tokens in query."""
    def overlap(a, b):
        tokens_a = {t for t in re.split(r"\W+", a.lower()) if len(t) > 2}
        if not tokens_a:
            return 0.0
        matched = sum(1 for t in tokens_a if t in b.lower())
        return matched / len(tokens_a)

    forward = overlap(query, candidate)
    backward = overlap(candidate, query)
    return forward >= threshold and backward >= threshold


def _search_spotify_track(sp, artist, track_name):
    """Use field-qualified query when artist is known; fall back to free-text."""
    if artist:
        query = f'artist:"{artist}" track:"{track_name}"'
    else:
        query = track_name

    results = sp.search(q=query, type="track", limit=1)
    tracks = results.get("tracks", {}).get("items", [])

    # If field-qualified search returns nothing, retry with free-text
    if not tracks and artist:
        results = sp.search(q=f"{artist} {track_name}", type="track", limit=1)
        tracks = results.get("tracks", {}).get("items", [])

    if not tracks:
        return None

    track = tracks[0]
    candidate = " ".join(a["name"] for a in track["artists"]) + " " + track["name"]
    full_query = f"{artist} {track_name}" if artist else track_name
    return track["id"] if _is_confident_match(full_query, candidate) else None


def extract_youtube_tracks(messages, sp):
    seen_video_ids = set()
    track_ids = []

    for message in messages:
        text = getattr(message, "text", None)
        if not text:
            continue
        for url, video_id in _extract_yt_urls_with_ids(text):
            if video_id in seen_video_ids:
                continue
            seen_video_ids.add(video_id)

            title = _fetch_yt_title(url)
            if not title:
                print(f"[YT] Could not fetch title for {url} — skipping")
                continue

            artist, track_name = _parse_title(title)
            track_id = _search_spotify_track(sp, artist, track_name)

            if track_id:
                print(f"[YT] Matched: '{title}' -> {track_id}")
                track_ids.append(track_id)
            else:
                query_repr = f"{artist} - {track_name}" if artist else track_name
                print(f"[YT] No confident match for: '{title}' (query: '{query_repr}')")

    return track_ids
