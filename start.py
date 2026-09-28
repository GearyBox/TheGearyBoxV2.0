from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import httpx
import time
import json
import requests
import sys
import re
from urllib.parse import quote, unquote

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# --- Config ---
PORT = 7050
HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36'}
#PROXIES = {'http': 'socks5h://127.0.0.1:9050','https': 'socks5h://127.0.0.1:9050'}

app = FastAPI()

#CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_title(imdb_id, content_type='movie'):
    """Fetches the title name from Cinemeta using IMDB ID and content type"""
    print(f"Fetching metadata for: {imdb_id} as {content_type}")

    try:
        url = f"https://v3-cinemeta.strem.io/meta/{content_type}/{imdb_id}.json"
        res = requests.get(url, timeout=5, headers=HEADERS)
        if res.status_code == 200:
            data = res.json()
            if data.get('meta'):
                meta = data['meta']
                title = meta.get('originalTitle') or meta.get('name')
                if title:
                    return title
    except Exception as e:
        print(f"Error fetching title form Cinemeta: {e}")
        pass

    # Fallback
    fallback_type = 'series' if content_type == 'movie' else 'movie'
    try:
        url = f"https://v3-cinemeta.strem.io/meta/{fallback_type}/{imdb_id}.json"
        res = requests.get(url, timeout=5, headers=HEADERS)
        if res.status_code == 200:
            data = res.json()
            if data.get('meta'):
                meta = data['meta']
                title = meta.get('originalTitle') or meta.get('name')
                if title:
                    print(f"  ⚠ Found as {fallback_type} instead of {content_type}, switching category")
                    return title
    except Exception as e:
        print(f"Error fetching title form Cinemeta fallback: {e}")
        pass

    return None


def get_torrents(query, content_type='movie'):
    safe_query = quote(query)

    if content_type == 'series':
        category = 200
    else:
        category = 200

    url = f"https://apibay.org/q.php?q={safe_query}&cat={category}"
    #  url = f"http://piratebayo3klnzokct3wt5yyxb2vpebbuyjl7m623iaxmqhsd52coid.onion/q.php?q={safe_query}&cat={category}"

    # Parse query 
    ep_match = re.search(r'[Ss](\d+)[Ee](\d+)', query)
    if ep_match:
        title_part = query[:ep_match.start()].strip()
        season_num = int(ep_match.group(1))
        episode_num = int(ep_match.group(2))
        title_words = [w.lower() for w in title_part.split() if w]
    else:
        title_words = [w.lower() for w in query.split() if w]
        season_num = None
        episode_num = None

    # --- LOGGING ---
    print(f"  API URL: {url}")
    print(f"  Required title words: {title_words}")
    if season_num is not None:
        print(f"  Required episode: S{season_num}E{episode_num}")
    # ---------------------

    allowed_keywords = ['1080p', '720p', '4k', '2160p', 'web', 'x265', 'x264', 'h264', 'h265', 'bluray']

    try:
        res = requests.get(url,  timeout=20, headers=HEADERS)    #proxies=PROXIES,
        if res.status_code == 200:
            data = res.json()
            if not isinstance(data, list):
                return []

            results = []
            for item in data:
                if item.get('id') == '0' or not item.get('info_hash'):
                    continue

                name = item.get('name', '')
                name_lower = name.lower()

                # Title AND filter
                if not all(word in name_lower for word in title_words):
                    continue

                # Flexible episode filter for series
                if season_num is not None and episode_num is not None:
                    ep_patterns = [
                        f's{season_num:02d}e{episode_num:02d}',
                        f's{season_num}e{episode_num}',
                        f's{season_num:02d} e{episode_num:02d}',
                        f'{season_num}x{episode_num:02d}',
                        f'{season_num}x{episode_num}',
                    ]
                    if not any(pat in name_lower for pat in ep_patterns):
                        continue

                # Quality Filtering
                if not any(keyword in name_lower for keyword in allowed_keywords):
                    continue

                try:
                    seeders = int(item.get('seeders', 0))
                except:
                    seeders = 0

                size_bytes = int(item.get('size', 0))
                size_str = f"{size_bytes / (1024**3):.1f} GB" if size_bytes > 1024**3 else f"{size_bytes / (1024**2):.0f} MB"

                results.append({
                    "name": "TGBxV2.0",
                    "title": f"{name}\n💾 {size_str} 👥 {seeders}",
                    "infoHash": item.get('info_hash'),
                    "_seeders": seeders,
                    "_megusta": "megusta" in name_lower and seeders >= 5
                })

            results.sort(
                key=lambda x: (
                    not x['_megusta'],
                    -x['_seeders']
                )
            )

            return results

    except Exception as e:
        print(f"  API Error: {e}")
        return []


# --- Server Logic ---

@app.get('/manifest.json')
def get_manifest():
    manifest = {
        "id": "python.pirate.standalone",
        "version": "2.0",
        "name": "TheGearyBoxV2",
        "description": "Stremio addon",
        "types": ["movie", "series"],
        "resources": ["stream"],
        "idPrefixes": ["tt"]
    }
    return manifest


@app.get('/stream/{request_type}/{file_name}')
def get_stream(request_type: str, file_name: str):
    full_id = unquote(file_name).replace('.json', '')

    print(f"Request Type: {request_type}, ID: {full_id}")

    clean_id = full_id.split(':')[0]
    title = get_title(clean_id, request_type)

    if not title:
        print(f"Title not found for {clean_id}")
        return {"streams": []}

    query = title.replace('&', 'and').replace("'", "").replace('- ', '').replace(':', '').replace('?', '').replace('!', '').replace('-', ' ')

    if request_type == 'series' and ':' in full_id:
        p = full_id.split(':')
        if len(p) >= 3:
            try:
                season = int(p[1])
                episode = int(p[2])
                query = f"{query} S{season:02d}E{episode:02d}"
            except:
                pass

    print(f"Searching for: {query}")
    streams = get_torrents(query, request_type)
    return {"streams": streams}


# --- Start Server ---
if __name__ == '__main__':
    print(f"Server running on http://127.0.0.1:7050")
    print("Press CTRL+C to stop")
    uvicorn.run("start:app", host="127.0.0.1", port=7050, log_level="info")

