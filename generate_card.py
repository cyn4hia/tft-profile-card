"""
tft stat generator yippeee
"""

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
PAST_RANKS = os.environ.get("PAST_RANKS", "")  
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "tft-stats.svg")
PROXY_URL = os.environ.get("PROXY_URL", "") 

def api_request(url: str) -> dict:
    """ auth to riot api """
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
    """get puuid from riot id"""
    encoded_name = urllib.parse.quote(game_name)
    encoded_tag = urllib.parse.quote(tag_line)
    url = f"https://{ROUTING}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_name}/{encoded_tag}"
    data = api_request(url)
    return data["puuid"]


def get_summoner_by_puuid(puuid: str) -> dict:
    """get summoner id"""
    url = f"https://{REGION}.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}"
    return api_request(url)


def get_ranked_stats(puuid: str) -> dict | None:
    """get tft ranked stats using puuid"""
    url = f"https://{REGION}.api.riotgames.com/tft/league/v1/entries/by-puuid/{puuid}"

def download_icon(icon_id: int, save_path: str = "profile-icon.png") -> str:
    """download png icon but also save here as backup"""
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
        print(f"  ⚠ Could not download icon: {e}", file=sys.stderr)
        return ""


def get_placeholder_icon_data_uri() -> str:
    """placeholder for icon"""
    placeholder_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">'
        '<rect width="64" height="64" rx="32" fill="#2a2a2a"/>'
        '<text x="32" y="38" fill="#666" font-size="20" text-anchor="middle" '
        'font-family="sans-serif">?</text></svg>'
    )
    b64 = base64.b64encode(placeholder_svg.encode()).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def get_match_ids(puuid: str, count: int = 20) -> list[str]:
    """get recent tft match ids"""
    url = f"https://{ROUTING}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?count={count}"
    return api_request(url)


def get_match_detail(match_id: str) -> dict:
    """get full match data"""
    url = f"https://{ROUTING}.api.riotgames.com/tft/match/v1/matches/{match_id}"
    return api_request(url)

def process_matches(puuid: str, match_ids: list[str]) -> dict:
    """analyze recent matches for stats"""
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


def parse_past_ranks(raw: str) -> list[dict]:
    """parse - format: 'Set10:Diamond,Set9:Platinum IV'"""
    if not raw.strip():
        return []
    ranks = []
    for entry in raw.split(","):
        entry = entry.strip()
        if ":" in entry:
            season, rank = entry.split(":", 1)
            ranks.append({"season": season.strip(), "rank": rank.strip()})
    return ranks

RANK_COLORS = {
    "IRON": "#6b6b6b",
    "BRONZE": "#a0522d",
    "SILVER": "#a8a8a8",
    "GOLD": "#d4a437",
    "PLATINUM": "#4eb5a1",
    "EMERALD": "#2d9e5c",
    "DIAMOND": "#6a7eff",
    "MASTER": "#9d4dbb",
    "GRANDMASTER": "#e34444",
    "CHALLENGER": "#f5c542",
}

def get_rank_color(tier: str) -> str:
    return RANK_COLORS.get(tier.upper(), "#91a8ff")


def escape_xml(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def generate_placement_sparkline(placements: list[int], x_start: int, y_center: int, width: int, height: int) -> str:
    """Generate a cute sparkline with rounded dots."""
    if not placements:
        return ""

    n = len(placements)
    step_x = width / max(n - 1, 1)
    scale_y = height / 7

    points = []
    dots = []
    for i, p in enumerate(placements):
        x = x_start + i * step_x
        y = y_center - height / 2 + (p - 1) * scale_y
        points.append(f"{x:.1f},{y:.1f}")

        color = "#7ec8e3" if p <= 4 else "#ffb3ba"
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}" stroke="white" stroke-width="1" opacity="0.95"/>')

    polyline = f'<polyline points="{" ".join(points)}" fill="none" stroke="#b8d4f0" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.4"/>'

    return polyline + "\n".join(dots)


def generate_star(cx: float, cy: float, size: float, opacity: float = 0.3) -> str:
    """Generate a tiny decorative star/sparkle."""
    h = size / 2
    return f'''<g opacity="{opacity}" transform="translate({cx},{cy})">
      <line x1="-{h}" y1="0" x2="{h}" y2="0" stroke="#a8d8ff" stroke-width="1" stroke-linecap="round"/>
      <line x1="0" y1="-{h}" x2="0" y2="{h}" stroke="#a8d8ff" stroke-width="1" stroke-linecap="round"/>
    </g>'''


def generate_svg(
    riot_id: str,
    tier: str,
    rank: str,
    lp: int,
    wins: int,
    losses: int,
    match_stats: dict,
    icon_data_uri: str,
    past_ranks: list[dict],
) -> str:
    """gen svg card"""

    display_name = escape_xml(riot_id)
    rank_color = get_rank_color(tier)
    tier_display = f"{tier.capitalize()} {rank}" if rank and rank != "I" and tier.upper() not in ("MASTER", "GRANDMASTER", "CHALLENGER") else tier.capitalize()
    total_games = wins + losses
    ranked_wr = (wins / total_games * 100) if total_games > 0 else 0

    icon_href = icon_data_uri if icon_data_uri else get_placeholder_icon_data_uri()

    card_w = 440
    card_h = 340
    if past_ranks:
        card_h += 50

    import random
    random.seed(42) 
    stars_svg = ""
    for _ in range(8):
        sx = random.randint(20, card_w - 20)
        sy = random.randint(10, card_h - 10)
        ss = random.uniform(4, 8)
        so = random.uniform(0.08, 0.2)
        stars_svg += generate_star(sx, sy, ss, so)

    past_ranks_svg = ""
    if past_ranks:
        y_pr = card_h - 65
        past_ranks_svg += f'<text x="28" y="{y_pr}" fill="#7a9cc6" font-size="10" font-family="\'Nunito\', \'Segoe UI\', sans-serif" font-weight="700" letter-spacing="1">✧ PAST SETS</text>'
        x_offset = 28
        for pr in past_ranks[:6]:
            label = f"{escape_xml(pr['season'])}: {escape_xml(pr['rank'])}"
            pill_w = len(label) * 6 + 20
            past_ranks_svg += f'''
            <rect x="{x_offset}" y="{y_pr + 8}" width="{pill_w:.0f}" height="22" rx="11" fill="#1e3a5f" stroke="#2a5080" stroke-width="0.5"/>
            <text x="{x_offset + pill_w / 2:.0f}" y="{y_pr + 22}" fill="#8bbce0" font-size="9" font-family="'Nunito', 'Segoe UI', sans-serif" font-weight="600" text-anchor="middle">{label}</text>
            '''
            x_offset += pill_w + 8

    sparkline_svg = generate_placement_sparkline(
        match_stats["placements"][:15][::-1], x_start=248, y_center=162, width=160, height=40
    )

    def stat_bubble(cx, cy, label, value, sub, color="#7ec8e3"):
        return f'''
        <circle cx="{cx}" cy="{cy}" r="38" fill="#0d2137" stroke="{color}" stroke-width="1.5" opacity="0.6"/>
        <text x="{cx}" y="{cy - 5}" fill="{color}" font-size="18" font-family="'Nunito', 'Segoe UI', sans-serif" font-weight="800" text-anchor="middle">{value}</text>
        <text x="{cx}" y="{cy + 10}" fill="#5a8ab5" font-size="8" font-family="'Nunito', 'Segoe UI', sans-serif" font-weight="600" text-anchor="middle" letter-spacing="0.5">{label}</text>
        <text x="{cx}" y="{cy + 22}" fill="#3d6d94" font-size="7.5" font-family="'Nunito', 'Segoe UI', sans-serif" text-anchor="middle">{sub}</text>
        '''

    stats_svg = stat_bubble(60, 165, "WIN RATE", f"{ranked_wr:.0f}%", f"{wins}W {losses}L", "#7ec8e3")
    stats_svg += stat_bubble(150, 165, "TOP 4", f"{match_stats['top4_rate']:.0f}%", f"{match_stats['top4']}/{match_stats['games_analyzed']}", "#98d4ee")
    stats_svg += stat_bubble(60, 260, "AVG PLACE", f"{match_stats['avg_placement']:.1f}", f"last {match_stats['games_analyzed']}", "#b0c4de")

    placement_bar = generate_placement_bar(match_stats["placements"], 145, 238, 260, 16)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{card_w}" height="{card_h}" viewBox="0 0 {card_w} {card_h}" fill="none">

  <defs>
    <clipPath id="avatar-clip">
      <circle cx="52" cy="54" r="28"/>
    </clipPath>
    <linearGradient id="bg-grad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0a1628"/>
      <stop offset="50%" stop-color="#0f2035"/>
      <stop offset="100%" stop-color="#0a1a30"/>
    </linearGradient>
    <linearGradient id="border-grad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#1e4a7a" stop-opacity="0.8"/>
      <stop offset="50%" stop-color="#2a6aaa" stop-opacity="0.4"/>
      <stop offset="100%" stop-color="#1e4a7a" stop-opacity="0.8"/>
    </linearGradient>
    <linearGradient id="top-bar" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#4a9eff" stop-opacity="0"/>
      <stop offset="30%" stop-color="{rank_color}"/>
      <stop offset="70%" stop-color="#7ec8e3"/>
      <stop offset="100%" stop-color="#4a9eff" stop-opacity="0"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.3" cy="0.2" r="0.7">
      <stop offset="0%" stop-color="#1a4a80" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="#0a1628" stop-opacity="0"/>
    </radialGradient>
    <filter id="soft-glow">
      <feGaussianBlur stdDeviation="2" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>

  <!-- Card Background -->
  <rect width="{card_w}" height="{card_h}" rx="16" fill="url(#bg-grad)"/>
  <rect width="{card_w}" height="{card_h}" rx="16" fill="url(#glow)"/>
  <rect width="{card_w}" height="{card_h}" rx="16" fill="none" stroke="url(#border-grad)" stroke-width="1.5"/>

  <!-- Top accent bar -->
  <rect x="40" y="0" width="{card_w - 80}" height="2.5" rx="1.25" fill="url(#top-bar)" opacity="0.8"/>

  <!-- Decorative sparkles -->
  {stars_svg}

  <!-- Avatar with glow ring -->
  <circle cx="52" cy="54" r="31" fill="none" stroke="{rank_color}" stroke-width="2" opacity="0.25" filter="url(#soft-glow)"/>
  <circle cx="52" cy="54" r="29.5" fill="none" stroke="{rank_color}" stroke-width="1.5" opacity="0.5"/>
  <circle cx="52" cy="54" r="28" fill="#0d2137"/>
  <image href="{icon_href}" x="24" y="26" width="56" height="56" clip-path="url(#avatar-clip)" preserveAspectRatio="xMidYMid slice"/>

  <!-- Riot ID -->
  <text x="94" y="44" fill="#d4e6f7" font-size="17" font-family="'Nunito', 'Segoe UI', sans-serif" font-weight="800">{display_name}</text>

  <!-- Rank badge pill -->
  <rect x="94" y="52" width="{len(tier_display) * 7.2 + 60:.0f}" height="24" rx="12" fill="{rank_color}" opacity="0.12" stroke="{rank_color}" stroke-width="0.5" stroke-opacity="0.3"/>
  <text x="106" y="69" fill="{rank_color}" font-size="12" font-family="'Nunito', 'Segoe UI', sans-serif" font-weight="700">✦ {escape_xml(tier_display)}</text>
  <text x="{111 + len(tier_display) * 7.2:.0f}" y="69" fill="#5a8ab5" font-size="11" font-family="'Nunito', 'Segoe UI', sans-serif" font-weight="600">{lp} LP</text>

  <!-- Cute divider with dots -->
  <line x1="28" y1="96" x2="{card_w - 28}" y2="96" stroke="#1a3a5a" stroke-width="1" stroke-dasharray="4,3" opacity="0.5"/>
  <circle cx="{card_w / 2}" cy="96" r="2" fill="#2a6aaa" opacity="0.6"/>

  <!-- TFT label -->
  <text x="{card_w - 28}" y="50" fill="#2a5a8a" font-size="9" font-family="'Nunito', 'Segoe UI', sans-serif" font-weight="700" text-anchor="end" letter-spacing="1.5">TEAMFIGHT TACTICS</text>

  <!-- Stat bubbles -->
  {stats_svg}

  <!-- Recent trend section -->
  <text x="248" y="120" fill="#5a8ab5" font-size="9" font-family="'Nunito', 'Segoe UI', sans-serif" font-weight="700" letter-spacing="1">✧ RECENT GAMES</text>

  <!-- Sparkline -->
  {sparkline_svg}

  <!-- Sparkline labels -->
  <text x="248" y="190" fill="#3d6d94" font-size="7.5" font-family="'Nunito', 'Segoe UI', sans-serif">8th</text>
  <text x="248" y="140" fill="#3d6d94" font-size="7.5" font-family="'Nunito', 'Segoe UI', sans-serif">1st</text>

  <!-- Placement spread -->
  <text x="145" y="230" fill="#5a8ab5" font-size="9" font-family="'Nunito', 'Segoe UI', sans-serif" font-weight="700" letter-spacing="1">✧ PLACEMENTS</text>
  {placement_bar} 

  <!-- Footer -->
  <text x="{card_w - 28}" y="{card_h - 16}" fill="#1e3a5a" font-size="8" font-family="'Nunito', 'Segoe UI', sans-serif" text-anchor="end">✦ Updated {datetime.now(timezone.utc).strftime('%b %d, %Y %H:%M UTC')}</text>
  <text x="28" y="{card_h - 16}" fill="#1e3a5a" font-size="8" font-family="'Nunito', 'Segoe UI', sans-serif">match history card designed by cindy!!</text>

  {past_ranks_svg}

</svg>'''

    return svg


def generate_placement_bar(placements: list[int], x: int, y: int, width: int, height: int) -> str:
    """gen the placement bar 1 - 8"""
    if not placements:
        return ""

    counts = [0] * 8
    for p in placements:
        if 1 <= p <= 8:
            counts[p - 1] += 1

    total = len(placements)

    colors = ["#5bcefa", "#7ed4f0", "#98dce8", "#b0e0e0", "#d4b8d4", "#e8a8b8", "#f0909a", "#f07080"]
    labels = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th"]

    svg = ""
    x_offset = x
    first = True
    last_i = max(i for i in range(8) if counts[i] > 0)
    for i in range(8):
        if counts[i] == 0:
            continue
        w = (counts[i] / total) * width
        rx = "8" if first and i == last_i else ("8 0 0 8" if first else ("0 8 8 0" if i == last_i else "0"))
        if first and i == last_i:
            svg += f'<rect x="{x_offset:.1f}" y="{y}" width="{w:.1f}" height="{height}" rx="8" fill="{colors[i]}" opacity="0.75"/>'
        else:
            svg += f'<rect x="{x_offset:.1f}" y="{y}" width="{w:.1f}" height="{height}" fill="{colors[i]}" opacity="0.75"/>'
        if w > 22:
            svg += f'<text x="{x_offset + w / 2:.1f}" y="{y + height / 2 + 3}" fill="#0a1628" font-size="7.5" font-family="\'Nunito\', \'Segoe UI\', sans-serif" font-weight="700" text-anchor="middle" opacity="0.8">{labels[i]}</text>'
        if first:
            first = False
        x_offset += w

    svg = f'<clipPath id="bar-clip"><rect x="{x}" y="{y}" width="{width}" height="{height}" rx="8"/></clipPath><g clip-path="url(#bar-clip)">{svg}</g>'

    return svg
CHIBI_COSMETICS = {
    "PetChibiLux": {
        "tactician_name": "Chibi Porcelain Lux",
        "arena": "Heaven's Celestial Court",
        "boom": "Porcelain Final Spark",
        "portal": "Porcelain Bloom",
        "arena_img": "cosmetics/koi-arena.jpg",
        "boom_img": "cosmetics/porcelain-boom.png",
        "portal_img": "cosmetics/porcelain-portal.png",
    }
}

def get_companion_from_match(puuid: str, match_ids: list[str]) -> dict | None:
    """get recent tactician used"""
    if not match_ids:
        return None
    try:
        match = get_match_detail(match_ids[0])
        for p in match.get("info", {}).get("participants", []):
            if p.get("puuid") == puuid:
                return p.get("companion", {})
    except Exception as e:
        print(f"  ⚠ Could not get companion data: {e}", file=sys.stderr)
    return None


def get_tactician_image_uri(item_id: int) -> str:
    """get tact img"""
    try:
        versions_url = "https://ddragon.leagueoflegends.com/api/versions.json"
        resp = req_lib.get(versions_url)
        latest = resp.json()[0]

        tact_url = f"https://ddragon.leagueoflegends.com/cdn/{latest}/data/en_US/tft-tactician.json"
        resp = req_lib.get(tact_url)
        tact_data = resp.json().get("data", {})

        entry = tact_data.get(str(item_id))
        if entry and entry.get("image", {}).get("full"):
            img_name = entry["image"]["full"]
            img_url = f"https://ddragon.leagueoflegends.com/cdn/{latest}/img/tft-tactician/{img_name}"
            resp = req_lib.get(img_url)
            if resp.status_code == 200:
                b64 = base64.b64encode(resp.content).decode("ascii")
                return f"data:image/png;base64,{b64}"
    except Exception as e:
        print(f"  ⚠ Could not fetch tactician image: {e}", file=sys.stderr)
    return ""


def load_image_as_data_uri(filepath: str) -> str:
    """Load a local image file and return as base64 data URI."""
    try:
        with open(filepath, "rb") as f:
            img_bytes = f.read()
        b64 = base64.b64encode(img_bytes).decode("ascii")
        ext = filepath.rsplit(".", 1)[-1].lower()
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(ext, "image/png")
        return f"data:{mime};base64,{b64}"
    except FileNotFoundError:
        return ""


def generate_cosmetics_svg(
    companion: dict,
    tactician_img_uri: str,
    cosmetics: dict,
) -> str:
    """generate cosmetics SVG"""

    species = companion.get("species", "Unknown")
    tactician_name = cosmetics.get("tactician_name", species.replace("PetChibi", "Chibi "))

    arena_uri = load_image_as_data_uri(cosmetics.get("arena_img", ""))
    boom_uri = load_image_as_data_uri(cosmetics.get("boom_img", ""))
    portal_uri = load_image_as_data_uri(cosmetics.get("portal_img", ""))

    card_w = 160
    card_h = 340

    def cosmetic_slot(y, label, name, img_uri):
        """generate one cosmetic slot with image and label"""
        if img_uri:
            img_el = f'''
            <clipPath id="clip-{label.lower()}"><rect x="30" y="{y}" width="100" height="40" rx="8"/></clipPath>
            <rect x="30" y="{y}" width="100" height="40" rx="8" fill="#0d2137"/>
            <image href="{img_uri}" x="30" y="{y}" width="100" height="40" clip-path="url(#clip-{label.lower()})" preserveAspectRatio="xMidYMid slice" opacity="0.8"/>
            '''
        else:
            img_el = f'''
            <rect x="30" y="{y}" width="100" height="40" rx="8" fill="#0d2137" stroke="#1a3a5a" stroke-width="0.5" stroke-dasharray="3,2"/>
            <text x="80" y="{y + 23}" fill="#2a5a8a" font-size="8" font-family="'Nunito', 'Segoe UI', sans-serif" text-anchor="middle">add image</text>
            '''
        return f'''
        <text x="80" y="{y - 6}" fill="#5a8ab5" font-size="8" font-family="'Nunito', 'Segoe UI', sans-serif" font-weight="700" text-anchor="middle" letter-spacing="0.8">{escape_xml(label.upper())}</text>
        {img_el}
        <text x="80" y="{y + 52}" fill="#3d6d94" font-size="7" font-family="'Nunito', 'Segoe UI', sans-serif" text-anchor="middle">{escape_xml(name)}</text>
        '''

    # Tactician section
    if tactician_img_uri:
        tact_img = f'''
        <clipPath id="clip-tact"><circle cx="80" cy="62" r="30"/></clipPath>
        <circle cx="80" cy="62" r="31" fill="none" stroke="#7ec8e3" stroke-width="1.5" opacity="0.4"/>
        <circle cx="80" cy="62" r="30" fill="#0d2137"/>
        <image href="{tactician_img_uri}" x="50" y="32" width="60" height="60" clip-path="url(#clip-tact)" preserveAspectRatio="xMidYMid slice"/>
        '''
    else:
        tact_img = f'''
        <circle cx="80" cy="62" r="30" fill="#0d2137" stroke="#1a3a5a" stroke-width="0.5" stroke-dasharray="3,2"/>
        <text x="80" y="66" fill="#2a5a8a" font-size="9" font-family="'Nunito', 'Segoe UI', sans-serif" text-anchor="middle">?</text>
        '''

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{card_w}" height="{card_h}" viewBox="0 0 {card_w} {card_h}" fill="none">

  <defs>
    <linearGradient id="cos-bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0a1628"/>
      <stop offset="100%" stop-color="#0a1a30"/>
    </linearGradient>
    <linearGradient id="cos-border" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#1e4a7a" stop-opacity="0.8"/>
      <stop offset="100%" stop-color="#1e4a7a" stop-opacity="0.4"/>
    </linearGradient>
  </defs>

  <!-- Card Background -->
  <rect width="{card_w}" height="{card_h}" rx="16" fill="url(#cos-bg)"/>
  <rect width="{card_w}" height="{card_h}" rx="16" fill="none" stroke="url(#cos-border)" stroke-width="1.5"/>

  <!-- Top accent -->
  <rect x="30" y="0" width="100" height="2.5" rx="1.25" fill="#7ec8e3" opacity="0.4"/>

  <!-- Title -->
  <text x="80" y="22" fill="#7a9cc6" font-size="9" font-family="'Nunito', 'Segoe UI', sans-serif" font-weight="700" text-anchor="middle" letter-spacing="1.5">✧ LOADOUT</text>

  <!-- Tactician -->
  {tact_img}
  <text x="80" y="104" fill="#d4e6f7" font-size="9" font-family="'Nunito', 'Segoe UI', sans-serif" font-weight="700" text-anchor="middle">{escape_xml(tactician_name)}</text>

  <!-- Cosmetic slots -->
  {cosmetic_slot(125, "Arena", cosmetics.get("arena", ""), arena_uri)}
  {cosmetic_slot(195, "Boom", cosmetics.get("boom", ""), boom_uri)}
  {cosmetic_slot(265, "Portal", cosmetics.get("portal", ""), portal_uri)}

  <!-- Footer -->
  <text x="80" y="{card_h - 10}" fill="#1e3a5a" font-size="7" font-family="'Nunito', 'Segoe UI', sans-serif" text-anchor="middle">♡ auto-detected</text>

</svg>'''

    return svg

def generate_mock_card() -> str:
    """mock card gen"""
    mock_match_stats = {
        "placements": [2, 4, 1, 6, 3, 5, 1, 4, 2, 7, 3, 1, 5, 2, 4],
        "games_analyzed": 15,
        "wins": 3,
        "top4": 10,
        "top4_rate": 66.7,
        "win_rate": 20.0,
        "avg_placement": 3.3,
    }
    return generate_svg(
        riot_id="YourName#TAG",
        tier="Diamond",
        rank="II",
        lp=75,
        wins=48,
        losses=32,
        match_stats=mock_match_stats,
        icon_data_uri=get_placeholder_icon_data_uri(),
        past_ranks=[
            {"season": "Set 10", "rank": "Master"},
            {"season": "Set 9", "rank": "Diamond I"},
        ],
    )

def main():

    if not RIOT_API_KEY and not PROXY_URL:
        print("No RIOT_API_KEY or PROXY_URL set. Generating preview card with mock data.")
        svg = generate_mock_card()
        with open(OUTPUT_PATH, "w") as f:
            f.write(svg)
        print(f"✓  Preview card saved to {OUTPUT_PATH}")
        return

    if RIOT_GAME_NAME and RIOT_TAG_LINE:
        game_name = RIOT_GAME_NAME
        tag_line = RIOT_TAG_LINE
    elif RIOT_ID and "#" in RIOT_ID:
        game_name, tag_line = RIOT_ID.rsplit("#", 1)
    else:
        print("Error: Set RIOT_GAME_NAME + RIOT_TAG_LINE, or RIOT_ID as 'Name#TAG'", file=sys.stderr)
        sys.exit(1)

    riot_id_display = f"{game_name}#{tag_line}"
    print(f"Fetching stats for {riot_id_display} on {REGION}...")

    puuid = get_puuid(game_name, tag_line)
    print(f"  PUUID: {puuid[:12]}...")

    summoner = get_summoner_by_puuid(puuid)
    print(f"  Summoner data keys: {list(summoner.keys())}")
    profile_icon_id = summoner.get("profileIconId", 1)
    print(f"  Profile Icon ID: {profile_icon_id}")

    icon_png_path = str(Path(OUTPUT_PATH).parent / "profile-icon.png")
    icon_data_uri = download_icon(profile_icon_id, save_path=icon_png_path)

    try:
        ranked = get_ranked_stats(puuid)
    except Exception:
        ranked = None

    tier = os.environ.get("TFT_RANK_TIER", "")
    rank = os.environ.get("TFT_RANK_DIVISION", "")
    lp = int(os.environ.get("TFT_RANK_LP", "0"))
    if tier:
        print(f"  Rank (manual): {tier} {rank} - {lp} LP")
    else:
        tier = "UNRANKED"
        print("  No rank set — add TFT_RANK_TIER env var to display rank.")

    match_ids = get_match_ids(puuid, count=MATCH_COUNT)
    print(f"  Found {len(match_ids)} matches. Analyzing...")

    if match_ids:
        print(f"  First match ID: {match_ids[0]}")

    if match_ids:
        first_match = get_match_detail(match_ids[0])
        info = first_match.get("info", {})
        print(f"  Queue ID: {info.get('queue_id', 'N/A')}")
        print(f"  Game type: {info.get('tft_game_type', 'N/A')}")
        print(f"  Set: {info.get('tft_set_number', 'N/A')}")
        print(f"  Participants: {len(info.get('participants', []))}")

    match_stats = process_matches(puuid, match_ids)
    print(f"  Placements: {match_stats['placements']}")
    print(f"  Avg placement: {match_stats['avg_placement']:.2f}, Top 4: {match_stats['top4_rate']:.1f}%")

    past_ranks = [
        {"season": "Set 15", "rank": "Diamond IV"},
        {"season": "Set 14", "rank": "Diamond IV"},
        {"season": "Set 13", "rank": "Emerald IV"},

    ]

    svg = generate_svg(
        riot_id=riot_id_display,
        tier=tier,
        rank=rank,
        lp=lp,
        wins=match_stats["wins"],
        losses=match_stats["games_analyzed"] - match_stats["wins"],
        match_stats=match_stats,
        icon_data_uri=icon_data_uri,
        past_ranks=past_ranks,
    )

    companion = get_companion_from_match(puuid, match_ids)
    if companion:
        species = companion.get("species", "")
        print(f"  Companion: {species} (item_ID: {companion.get('item_ID')}, skin_ID: {companion.get('skin_ID')})")

        cosmetics = CHIBI_COSMETICS.get(species, {})
        if cosmetics:

            tact_uri = get_tactician_image_uri(companion.get("item_ID", 0))
            if tact_uri:
                print(f"  ✓ Fetched tactician image from Data Dragon")
            else:
                print(f"  ⚠ Could not fetch tactician image")

            cosmetics_svg = generate_cosmetics_svg(companion, tact_uri, cosmetics)
            cosmetics_path = str(Path(OUTPUT_PATH).parent / "tft-cosmetics.svg")
            with open(cosmetics_path, "w") as f:
                f.write(cosmetics_svg)
            print(f"✓  Cosmetics card saved to {cosmetics_path}")
        else:
            print(f"  ⚠ No cosmetics mapping for {species}. Add it to CHIBI_COSMETICS.")
    else:
        print("  ⚠ Could not detect companion from match data.")

    with open(OUTPUT_PATH, "w") as f:
        f.write(svg)

    print(f"✓  Card saved to {OUTPUT_PATH}")




if __name__ == "__main__":
    main()