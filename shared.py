import os
import sys
import json
import base64
import urllib.parse
import requests as req_lib
from datetime import datetime, timezone
from pathlib import Path

RIOT_API_KEY = os.environ.get("RIOT_API_KEY", "")
RIOT_GAME_NAME = os.environ.get("RIOT_GAME_NAME", "")
RIOT_TAG_LINE = os.environ.get("RIOT_TAG_LINE", "")
RIOT_ID = os.environ.get("RIOT_ID", "")
REGION = os.environ.get("REGION", "na1")
ROUTING = os.environ.get("ROUTING", "americas")
PROFILE_IMAGE_URL = os.environ.get("PROFILE_IMAGE_URL", "")
MATCH_COUNT = int(os.environ.get("MATCH_COUNT", "20"))
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "tft-stats.svg")
PROXY_URL = os.environ.get("PROXY_URL", "")


def api_request(url: str) -> dict:
    """api request"""
    headers = {
        "X-Riot-Token": RIOT_API_KEY,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    resp = req_lib.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"API Error {resp.status_code}: {resp.text[:500]}", file=sys.stderr)
        resp.raise_for_status()
    return resp.json()


def get_puuid(game_name: str, tag_line: str) -> str:
    """get puuid from riot api"""
    encoded_name = urllib.parse.quote(game_name)
    encoded_tag = urllib.parse.quote(tag_line)
    url = f"https://{ROUTING}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_name}/{encoded_tag}"
    data = api_request(url)
    return data["puuid"]


def get_summoner_by_puuid(puuid: str) -> dict:
    """get summoner info by puuid"""
    url = f"https://{REGION}.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}"
    return api_request(url)


def get_match_ids(puuid: str, count: int = 20) -> list[str]:
    """return match ids"""
    url = f"https://{ROUTING}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?count={count}"
    return api_request(url)


def get_match_detail(match_id: str) -> dict:
    """return match detail"""
    url = f"https://{ROUTING}.api.riotgames.com/tft/match/v1/matches/{match_id}"
    return api_request(url)


def download_icon(icon_id: int, save_path: str = "profile-icon.png") -> str:
    """download profile icon from riot api"""
    url = PROFILE_IMAGE_URL if PROFILE_IMAGE_URL else f"https://ddragon.leagueoflegends.com/cdn/14.24.1/img/profileicon/{icon_id}.png"
    try:
        resp = req_lib.get(url)
        img_bytes = resp.content
        with open(save_path, "wb") as f:
            f.write(img_bytes)
        print(f"  Icon saved to {save_path}")
        b64 = base64.b64encode(img_bytes).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        print(f"  could not download icon: {e}", file=sys.stderr)
        return ""


def get_placeholder_icon_data_uri() -> str:
    """returns placeholder icon"""
    placeholder_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">'
        '<rect width="64" height="64" rx="32" fill="#2a2a2a"/>'
        '<text x="32" y="38" fill="#666" font-size="20" text-anchor="middle" '
        'font-family="sans-serif">?</text></svg>'
    )
    b64 = base64.b64encode(placeholder_svg.encode()).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def escape_xml(text: str) -> str:
    """escape xml special characters"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def load_image_as_data_uri(filepath: str) -> str:
    """load local image as data uri"""
    try:
        with open(filepath, "rb") as f:
            img_bytes = f.read()
        b64 = base64.b64encode(img_bytes).decode("ascii")
        ext = filepath.rsplit(".", 1)[-1].lower()
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(ext, "image/png")
        return f"data:{mime};base64,{b64}"
    except FileNotFoundError:
        return ""


def process_matches(puuid: str, match_ids: list[str]) -> dict:
    """process match data to extract placements and stats"""
    placements = []
    top4_count = 0
    wins = 0
    total_analyzed = 0

    for mid in match_ids:
        try:
            match = get_match_detail(mid)
            info = match.get("info", {})
            participants = info.get("participants", [])
            for p in participants:
                if p.get("puuid") == puuid:
                    placement = p.get("placement", 0)
                    placements.append(placement)
                    if placement <= 4:
                        top4_count += 1
                    if placement == 1:
                        wins += 1
                    total_analyzed += 1
                    break
        except Exception as e:
            print(f"Skipping match {mid}: {e}", file=sys.stderr)
            continue

    avg_placement = sum(placements) / len(placements) if placements else 0

    return {
        "placements": placements,
        "games_analyzed": total_analyzed,
        "wins": wins,
        "top4": top4_count,
        "top4_rate": (top4_count / total_analyzed * 100) if total_analyzed else 0,
        "win_rate": (wins / total_analyzed * 100) if total_analyzed else 0,
        "avg_placement": avg_placement,
    }


def resolve_riot_id():
    """resolve riot id from environment variables"""
    if RIOT_GAME_NAME and RIOT_TAG_LINE:
        return RIOT_GAME_NAME, RIOT_TAG_LINE
    elif RIOT_ID and "#" in RIOT_ID:
        return RIOT_ID.rsplit("#", 1)
    else:
        print("Error: Set RIOT_GAME_NAME + RIOT_TAG_LINE, or RIOT_ID as 'Name#TAG'", file=sys.stderr)
        sys.exit(1)
