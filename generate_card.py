"""
TFT Stats Card Generator for GitHub README
Fetches TFT stats from the Riot Games API and generates a clean SVG card.
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.error
import urllib.parse
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
    """Make request to Riot API, optionally through a Cloudflare Worker proxy."""
    if PROXY_URL:
        proxy = f"{PROXY_URL.rstrip('/')}/?url={urllib.parse.quote(url, safe='')}"
        req = urllib.request.Request(proxy)
    else:
        req = urllib.request.Request(url, headers={"X-Riot-Token": RIOT_API_KEY})

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"API Error {e.code}: {e.read().decode()}", file=sys.stderr)
        raise

def get_puuid(game_name: str, tag_line: str) -> str:
    """Get PUUID from Riot ID (gameName#tagLine)."""
    encoded_name = urllib.parse.quote(game_name)
    encoded_tag = urllib.parse.quote(tag_line)
    url = f"https://{ROUTING}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_name}/{encoded_tag}"
    data = api_request(url)
    return data["puuid"]


def get_summoner_by_puuid(puuid: str) -> dict:
    """Get summoner data (for profile icon ID)."""
    url = f"https://{REGION}.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}"
    return api_request(url)


def get_ranked_stats(summoner_id: str) -> dict | None:
    """Get TFT ranked stats for a summoner."""
    url = f"https://{REGION}.api.riotgames.com/tft/league/v1/entries/by-summoner/{summoner_id}"
    entries = api_request(url)
    for entry in entries:
        if entry.get("queueType") == "RANKED_TFT":
            return entry
    return None


def download_icon(icon_id: int, save_path: str = "profile-icon.png") -> str:
    """Download profile icon from Data Dragon and return base64 data URI.
    Also saves the PNG as a backup file."""
    url = PROFILE_IMAGE_URL if PROFILE_IMAGE_URL else f"https://ddragon.leagueoflegends.com/cdn/14.24.1/img/profileicon/{icon_id}.png"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TFT-Stats-Card/1.0"})
        with urllib.request.urlopen(req) as resp:
            img_bytes = resp.read()

        with open(save_path, "wb") as f:
            f.write(img_bytes)
        print(f"  Icon saved to {save_path}")

        b64 = base64.b64encode(img_bytes).decode("ascii")
        return f"data:image/png;base64,{b64}"

    except Exception as e:
        print(f"  ⚠ Could not download icon: {e}", file=sys.stderr)
        return ""


def get_placeholder_icon_data_uri() -> str:
    """Generate a simple placeholder circle as an SVG data URI for mock/fallback."""
    placeholder_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">'
        '<rect width="64" height="64" rx="32" fill="#2a2a2a"/>'
        '<text x="32" y="38" fill="#666" font-size="20" text-anchor="middle" '
        'font-family="sans-serif">?</text></svg>'
    )
    b64 = base64.b64encode(placeholder_svg.encode()).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def get_match_ids(puuid: str, count: int = 20) -> list[str]:
    """Get recent TFT match IDs."""
    url = f"https://{ROUTING}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?count={count}"
    return api_request(url)


def get_match_detail(match_id: str) -> dict:
    """Get full match data."""
    url = f"https://{ROUTING}.api.riotgames.com/tft/match/v1/matches/{match_id}"
    return api_request(url)

def process_matches(puuid: str, match_ids: list[str]) -> dict:
    """Analyze recent matches for stats."""
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
    """Parse PAST_RANKS env var. Format: 'Set10:Diamond,Set9:Platinum IV'"""
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
    return RANK_COLORS.get(tier.upper(), "#888888")


def escape_xml(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def generate_placement_sparkline(placements: list[int], x_start: int, y_center: int, width: int, height: int) -> str:
    """Generate an SVG sparkline for recent placements."""
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

        # Color dot based on placement
        color = "#4ade80" if p <= 4 else "#f87171"
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="{color}" opacity="0.9"/>')

    polyline = f'<polyline points="{" ".join(points)}" fill="none" stroke="#555" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" opacity="0.5"/>'

    return polyline + "\n".join(dots)


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
    """Generate the complete SVG stats card."""

    display_name = escape_xml(riot_id)
    rank_color = get_rank_color(tier)
    tier_display = f"{tier.capitalize()} {rank}" if rank and rank != "I" and tier.upper() not in ("MASTER", "GRANDMASTER", "CHALLENGER") else tier.capitalize()
    total_games = wins + losses
    ranked_wr = (wins / total_games * 100) if total_games > 0 else 0

    icon_href = icon_data_uri if icon_data_uri else get_placeholder_icon_data_uri()

    card_w = 420
    card_h = 320
    if past_ranks:
        card_h += 50

    past_ranks_svg = ""
    if past_ranks:
        y_pr = card_h - 62
        past_ranks_svg += f'<text x="24" y="{y_pr}" fill="#888" font-size="10" font-family="\'Segoe UI\', sans-serif" font-weight="600" letter-spacing="0.5">PAST SEASONS</text>'
        x_offset = 24
        for pr in past_ranks[:6]:  # max 6
            label = f"{escape_xml(pr['season'])}: {escape_xml(pr['rank'])}"
            pill_w = len(label) * 6.2 + 16
            past_ranks_svg += f'''
            <rect x="{x_offset}" y="{y_pr + 6}" width="{pill_w:.0f}" height="20" rx="4" fill="#2a2a2a"/>
            <text x="{x_offset + pill_w / 2:.0f}" y="{y_pr + 19}" fill="#aaa" font-size="9.5" font-family="'Segoe UI', sans-serif" text-anchor="middle">{label}</text>
            '''
            x_offset += pill_w + 6

    sparkline_svg = generate_placement_sparkline(
        match_stats["placements"][-15:], x_start=240, y_center=152, width=150, height=40
    )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{card_w}" height="{card_h}" viewBox="0 0 {card_w} {card_h}" fill="none">

  <defs>
    <clipPath id="avatar-clip">
      <circle cx="52" cy="56" r="26"/>
    </clipPath>
    <linearGradient id="rank-glow" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{rank_color}" stop-opacity="0.15"/>
      <stop offset="100%" stop-color="{rank_color}" stop-opacity="0"/>
    </linearGradient>
    <filter id="shadow" x="-4%" y="-4%" width="108%" height="108%">
      <feDropShadow dx="0" dy="1" stdDeviation="3" flood-color="#000" flood-opacity="0.3"/>
    </filter>
  </defs>

  <!-- Card Background -->
  <rect width="{card_w}" height="{card_h}" rx="12" fill="#161616" stroke="#2a2a2a" stroke-width="1"/>
  <rect width="{card_w}" height="{card_h}" rx="12" fill="url(#rank-glow)"/>

  <!-- Top accent line -->
  <rect x="0" y="0" width="{card_w}" height="3" rx="1.5" fill="{rank_color}" opacity="0.6"/>

  <!-- Avatar -->
  <circle cx="52" cy="56" r="27" fill="none" stroke="{rank_color}" stroke-width="2" opacity="0.7"/>
  <image href="{icon_href}" x="26" y="30" width="52" height="52" clip-path="url(#avatar-clip)" preserveAspectRatio="xMidYMid slice"/>

  <!-- Riot ID -->
  <text x="90" y="48" fill="#eee" font-size="16" font-family="'Segoe UI', sans-serif" font-weight="700">{display_name}</text>

  <!-- Rank badge -->
  <rect x="90" y="56" width="{len(tier_display) * 7.5 + 20:.0f}" height="22" rx="4" fill="{rank_color}" opacity="0.15"/>
  <text x="100" y="72" fill="{rank_color}" font-size="12" font-family="'Segoe UI', sans-serif" font-weight="600">{escape_xml(tier_display)}</text>
  <text x="{100 + len(tier_display) * 7.5:.0f}" y="72" fill="#888" font-size="11" font-family="'Segoe UI', sans-serif">{lp} LP</text>

  <!-- Divider -->
  <line x1="24" y1="98" x2="{card_w - 24}" y2="98" stroke="#2a2a2a" stroke-width="1"/>

  <!-- Stats Grid -->
  <!-- Win Rate (ranked) -->
  <text x="24" y="120" fill="#888" font-size="10" font-family="'Segoe UI', sans-serif" font-weight="600" letter-spacing="0.5">RANKED W/L</text>
  <text x="24" y="140" fill="#eee" font-size="18" font-family="'Segoe UI', sans-serif" font-weight="700">{ranked_wr:.1f}%</text>
  <text x="24" y="155" fill="#666" font-size="10" font-family="'Segoe UI', sans-serif">{wins}W {losses}L</text>

  <!-- Top 4 Rate -->
  <text x="130" y="120" fill="#888" font-size="10" font-family="'Segoe UI', sans-serif" font-weight="600" letter-spacing="0.5">TOP 4 RATE</text>
  <text x="130" y="140" fill="#eee" font-size="18" font-family="'Segoe UI', sans-serif" font-weight="700">{match_stats['top4_rate']:.1f}%</text>
  <text x="130" y="155" fill="#666" font-size="10" font-family="'Segoe UI', sans-serif">{match_stats['top4']}/{match_stats['games_analyzed']} games</text>

  <!-- Avg Placement -->
  <text x="240" y="120" fill="#888" font-size="10" font-family="'Segoe UI', sans-serif" font-weight="600" letter-spacing="0.5">RECENT TREND</text>

  <!-- Sparkline -->
  {sparkline_svg}

  <!-- Recent match stats summary -->
  <text x="24" y="185" fill="#888" font-size="10" font-family="'Segoe UI', sans-serif" font-weight="600" letter-spacing="0.5">AVG PLACEMENT</text>
  <text x="24" y="208" fill="#eee" font-size="22" font-family="'Segoe UI', sans-serif" font-weight="700">{match_stats['avg_placement']:.1f}</text>
  <text x="70" y="208" fill="#666" font-size="10" font-family="'Segoe UI', sans-serif">last {match_stats['games_analyzed']} games</text>

  <!-- Placement distribution bar -->
  <text x="24" y="235" fill="#888" font-size="10" font-family="'Segoe UI', sans-serif" font-weight="600" letter-spacing="0.5">PLACEMENT SPREAD</text>
  {generate_placement_bar(match_stats["placements"], 24, 244, card_w - 48, 14)}

  <!-- Footer -->
  <text x="{card_w - 24}" y="{card_h - 14}" fill="#444" font-size="9" font-family="'Segoe UI', sans-serif" text-anchor="end">Updated {datetime.now(timezone.utc).strftime('%b %d, %Y %H:%M UTC')}</text>
  <text x="24" y="{card_h - 14}" fill="#444" font-size="9" font-family="'Segoe UI', sans-serif">Teamfight Tactics</text>

  {past_ranks_svg}

</svg>'''

    return svg


def generate_placement_bar(placements: list[int], x: int, y: int, width: int, height: int) -> str:
    """Generate a horizontal stacked bar showing placement distribution."""
    if not placements:
        return ""

    counts = [0] * 8
    for p in placements:
        if 1 <= p <= 8:
            counts[p - 1] += 1

    total = len(placements)
    colors = ["#4ade80", "#86efac", "#bef264", "#fde047", "#fbbf24", "#fb923c", "#f87171", "#ef4444"]
    labels = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th"]

    svg = ""
    x_offset = x
    for i in range(8):
        if counts[i] == 0:
            continue
        w = (counts[i] / total) * width
        svg += f'<rect x="{x_offset:.1f}" y="{y}" width="{w:.1f}" height="{height}" rx="2" fill="{colors[i]}" opacity="0.7"/>'
        if w > 20:
            svg += f'<text x="{x_offset + w / 2:.1f}" y="{y + height / 2 + 3.5}" fill="#000" font-size="8" font-family="\'Segoe UI\', sans-serif" font-weight="600" text-anchor="middle" opacity="0.8">{labels[i]}</text>'
        x_offset += w

    return svg

def generate_mock_card() -> str:
    """Generate a card with placeholder data for preview/testing."""
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

    if not RIOT_API_KEY:
        print("⚠  No RIOT_API_KEY set. Generating preview card with mock data.")
        svg = generate_mock_card()
        with open(OUTPUT_PATH, "w") as f:
            f.write(svg)
        print(f"✓  Preview card saved to {OUTPUT_PATH}")
        return

    # Resolve Riot ID from either split env vars or combined RIOT_ID
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
    profile_icon_id = summoner.get("profileIconId", 1)
    print(f"  Profile Icon ID: {profile_icon_id}")

    icon_png_path = str(Path(OUTPUT_PATH).parent / "profile-icon.png")
    icon_data_uri = download_icon(profile_icon_id, save_path=icon_png_path)

    ranked = get_ranked_stats(summoner["id"])
    if ranked:
        tier = ranked.get("tier", "UNRANKED")
        rank = ranked.get("rank", "")
        lp = ranked.get("leaguePoints", 0)
        wins = ranked.get("wins", 0)
        losses = ranked.get("losses", 0)
        print(f"  Rank: {tier} {rank} - {lp} LP ({wins}W/{losses}L)")
    else:
        tier, rank, lp, wins, losses = "UNRANKED", "", 0, 0, 0
        print("  No ranked data found.")

    match_ids = get_match_ids(puuid, count=MATCH_COUNT)
    print(f"  Found {len(match_ids)} matches. Analyzing...")

    match_stats = process_matches(puuid, match_ids)
    print(f"  Avg placement: {match_stats['avg_placement']:.2f}, Top 4: {match_stats['top4_rate']:.1f}%")

    past_ranks = parse_past_ranks(PAST_RANKS)

    svg = generate_svg(
        riot_id=riot_id_display,
        tier=tier,
        rank=rank,
        lp=lp,
        wins=wins,
        losses=losses,
        match_stats=match_stats,
        icon_data_uri=icon_data_uri,
        past_ranks=past_ranks,
    )

    with open(OUTPUT_PATH, "w") as f:
        f.write(svg)

    print(f"✓  Card saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()