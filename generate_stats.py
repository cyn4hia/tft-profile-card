"""
tft stats card
"""
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from shared import *
from font import FREDOKA_FONT_FACE

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


def generate_placement_sparkline(placements, x_start, y_center, width, height):
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


def generate_star(cx, cy, size, opacity=0.3):
    h = size / 2
    return f'''<g opacity="{opacity}" transform="translate({cx},{cy})">
      <line x1="-{h}" y1="0" x2="{h}" y2="0" stroke="#a8d8ff" stroke-width="1" stroke-linecap="round"/>
      <line x1="0" y1="-{h}" x2="0" y2="{h}" stroke="#a8d8ff" stroke-width="1" stroke-linecap="round"/>
    </g>'''


def generate_placement_bar(placements, x, y, width, height):
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
        if first and i == last_i:
            svg += f'<rect x="{x_offset:.1f}" y="{y}" width="{w:.1f}" height="{height}" rx="8" fill="{colors[i]}" opacity="0.75"/>'
        else:
            svg += f'<rect x="{x_offset:.1f}" y="{y}" width="{w:.1f}" height="{height}" fill="{colors[i]}" opacity="0.75"/>'
        if w > 22:
            svg += f'<text x="{x_offset + w / 2:.1f}" y="{y + height / 2 + 3}" fill="#0a1628" font-size="8.5" font-family="\'Fredoka\', \'Segoe UI\', sans-serif" font-weight="700" text-anchor="middle" opacity="0.8">{labels[i]}</text>'
        if first:
            first = False
        x_offset += w
    svg = f'<clipPath id="bar-clip"><rect x="{x}" y="{y}" width="{width}" height="{height}" rx="8"/></clipPath><g clip-path="url(#bar-clip)">{svg}</g>'
    return svg

def generate_svg(riot_id, tier, rank, lp, wins, losses, match_stats, icon_data_uri, past_ranks):
    display_name = escape_xml(riot_id)
    rank_color = get_rank_color(tier)
    tier_display = f"{tier.capitalize()} {rank}" if rank and rank != "I" and tier.upper() not in ("MASTER", "GRANDMASTER", "CHALLENGER") else tier.capitalize()
    total_games = wins + losses
    ranked_wr = (wins / total_games * 100) if total_games > 0 else 0
    icon_href = icon_data_uri if icon_data_uri else get_placeholder_icon_data_uri()

    card_w = 440
    card_h = 390

    past_ranks_svg = ""
    if past_ranks:
        y_pr = card_h - 115
        past_ranks_svg += f'<text x="20" y="{y_pr}" fill="#7a9cc6" font-size="10" font-family="\'Fredoka\', \'Segoe UI\', sans-serif" font-weight="700" letter-spacing="1">✧ PAST SETS</text>'
        x_offset = 20
        for pr in past_ranks[:6]:
            label = f"{escape_xml(pr['season'])}: {escape_xml(pr['rank'])}"
            pill_w = len(label) * 6 + 20
            past_ranks_svg += f'''
            <rect x="{x_offset}" y="{y_pr + 8}" width="{pill_w:.0f}" height="22" rx="11" fill="#1e3a5f" stroke="#2a5080" stroke-width="0.5"/>
            <text x="{x_offset + pill_w / 2:.0f}" y="{y_pr + 22}" fill="#8bbce0" font-size="9" font-family="'Fredoka', 'Segoe UI', sans-serif" font-weight="600" text-anchor="middle">{label}</text>
            '''
            x_offset += pill_w + 8
    good_comp_svg = ""
    y_comp = card_h - 55
    x_offset = 20
    good_text = "Void Fast 10 Kai'Sa"
    good_pill_w = len(good_text) * 5 + 16
    good_x = 20
    good_comp_svg += f'<rect x="{good_x}" y="{y_comp + 1}" width="{good_pill_w:.0f}" height="20" rx="11" fill="#96D294" stroke="#2a5080" stroke-width="0.5"/>'
    good_comp_svg += f'<text x="{good_x + good_pill_w / 2:.0f}" y="{y_comp + 15}" fill="#FFFFFF" font-size="9" font-family="\'Fredoka\', \'Segoe UI\', sans-serif" font-weight="600" text-anchor="middle">Void Fast 10 Kai\'Sa</text>'

    bad_comp_svg = ""
    y_bad_comp = card_h - 55
    x_offset = 220
    bad_text = "Warwick Zaun"
    bad_pill_w = len(bad_text) * 5 + 16
    bad_x = 220
    bad_comp_svg += f'<rect x="{bad_x}" y="{y_bad_comp + 1}" width="{bad_pill_w:.0f}" height="20" rx="11" fill="#FF6961" stroke="#2a5080" stroke-width="0.5"/>'
    bad_comp_svg += f'<text x="{bad_x + bad_pill_w / 2:.0f}" y="{y_bad_comp + 15}" fill="#FFFFFF" font-size="9" font-family="\'Fredoka\', \'Segoe UI\', sans-serif" font-weight="600" text-anchor="middle">Warwick Zaun</text>'

    sparkline_svg = generate_placement_sparkline(
        match_stats["placements"][:15][::-1], x_start=248, y_center=162, width=160, height=40
    )

    def stat_bubble(cx, cy, label, value, sub, color="#7ec8e3"):
        return f'''
        <circle cx="{cx}" cy="{cy}" r="38" fill="#0d2137" stroke="{color}" stroke-width="1.5" opacity="0.6"/>
        <text x="{cx}" y="{cy - 5}" fill="{color}" font-size="18" font-family="'Fredoka', 'Segoe UI', sans-serif" font-weight="800" text-anchor="middle">{value}</text>
        <text x="{cx}" y="{cy + 10}" fill="#5a8ab5" font-size="8" font-family="'Fredoka', 'Segoe UI', sans-serif" font-weight="600" text-anchor="middle" letter-spacing="0.5">{label}</text>
        <text x="{cx}" y="{cy + 22}" fill="#3d6d94" font-size="7.5" font-family="'Fredoka', 'Segoe UI', sans-serif" text-anchor="middle">{sub}</text>
        '''

    stats_svg = stat_bubble(60, 155, "WIN RATE", f"{match_stats['top4_rate']:.0f}%", f"{match_stats['top4']}W {match_stats['games_analyzed']}L", "#98d4ee")
    stats_svg += stat_bubble(155, 155, "AVG PLACE", f"{match_stats['avg_placement']:.1f}", f"last {match_stats['games_analyzed']}", "#b0c4de")

    placement_bar = generate_placement_bar(match_stats["placements"], 20, 232, 400, 20)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
        width="{card_w}" height="{card_h}" viewBox="0 0 {card_w} {card_h}" fill="none">

    {FREDOKA_FONT_FACE}

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

  <rect width="{card_w}" height="{card_h}" rx="16" fill="url(#bg-grad)"/>
  <rect width="{card_w}" height="{card_h}" rx="16" fill="url(#glow)"/>
  <rect width="{card_w}" height="{card_h}" rx="16" fill="none" stroke="url(#border-grad)" stroke-width="1.5"/>

  <rect x="40" y="0" width="{card_w - 80}" height="2.5" rx="1.25" fill="url(#top-bar)" opacity="0.8"/>


  <circle cx="52" cy="54" r="31" fill="none" stroke="{rank_color}" stroke-width="2" opacity="0.25" filter="url(#soft-glow)"/>
  <circle cx="52" cy="54" r="29.5" fill="none" stroke="{rank_color}" stroke-width="1.5" opacity="0.5"/>
  <circle cx="52" cy="54" r="28" fill="#0d2137"/>
  <image href="{icon_href}" x="24" y="26" width="56" height="56" clip-path="url(#avatar-clip)" preserveAspectRatio="xMidYMid slice"/>

  <text x="94" y="44" fill="#d4e6f7" font-size="17" font-family="'Fredoka', 'Segoe UI', sans-serif" font-weight="800">{display_name}</text>

  <rect x="94" y="52" width="{len(tier_display) * 7.2 + 60:.0f}" height="24" rx="12" fill="{rank_color}" opacity="0.12" stroke="{rank_color}" stroke-width="0.5" stroke-opacity="0.3"/>
  <text x="106" y="69" fill="{rank_color}" font-size="12" font-family="'Fredoka', 'Segoe UI', sans-serif" font-weight="700">✦ {escape_xml(tier_display)}</text>
  <text x="{111 + len(tier_display) * 7.2:.0f}" y="69" fill="#5a8ab5" font-size="11" font-family="'Fredoka', 'Segoe UI', sans-serif" font-weight="600">{lp} LP</text>

  <line x1="28" y1="96" x2="{card_w - 28}" y2="96" stroke="#1a3a5a" stroke-width="1" stroke-dasharray="4,3" opacity="0.5"/>
  <circle cx="{card_w / 2}" cy="96" r="2" fill="#2a6aaa" opacity="0.6"/>

  <text x="{card_w - 28}" y="50" fill="#2a5a8a" font-size="9" font-family="'Fredoka', 'Segoe UI', sans-serif" font-weight="700" text-anchor="end" letter-spacing="1.5">TEAMFIGHT TACTICS</text>

  {stats_svg}

  <text x="228" y="120" fill="#5a8ab5" font-size="9" font-family="'Fredoka', 'Segoe UI', sans-serif" font-weight="700" letter-spacing="1">✧ RECENT GAMES</text>

  {sparkline_svg}

  <text x="228" y="193" fill="#3d6d94" font-size="7.5" font-family="'Fredoka', 'Segoe UI', sans-serif">8th</text>
  <text x="228" y="140" fill="#3d6d94" font-size="7.5" font-family="'Fredoka', 'Segoe UI', sans-serif">1st</text>

  <text x="20" y="225" fill="#5a8ab5" font-size="10" font-family="'Fredoka', 'Segoe UI', sans-serif" font-weight="700" letter-spacing="1">✧ PLACEMENTS</text>
  {placement_bar}

  <text x="20" y="328" fill="#5a8ab5" font-size="10" font-family="'Fredoka', 'Segoe UI', sans-serif" xml:space="preserve">FAVORITE COMP:</text>
  <text x="220" y="328" fill="#5a8ab5" font-size="10" font-family="'Fredoka', 'Segoe UI', sans-serif" xml:space="preserve">HATED COMP:</text>
  {good_comp_svg}
  {bad_comp_svg}

  <text x="{card_w - 20}" y="{card_h - 16}" fill="#1e3a5a" font-size="8" font-family="'Fredoka', 'Segoe UI', sans-serif" text-anchor="end">✦ Updated {datetime.now(timezone.utc).strftime('%b %d, %Y %H:%M UTC')}</text>
  <text x="20" y="{card_h - 16}" fill="#1e3a5a" font-size="8" font-family="'Fredoka', 'Segoe UI', sans-serif">match history card designed by cindy!!</text>

  {past_ranks_svg}

</svg>'''

    return svg


def main():
    if not RIOT_API_KEY and not PROXY_URL:
        mock_match_stats = {
            "placements": [2, 4, 1, 6, 3, 5, 1, 4, 2, 7, 3, 1, 5, 2, 4],
            "games_analyzed": 15, "wins": 3, "top4": 10,
            "top4_rate": 66.7, "win_rate": 20.0, "avg_placement": 3.3,
        }
        svg = generate_svg(
            riot_id="YourName#TAG", tier="Diamond", rank="II", lp=75,
            wins=48, losses=32, match_stats=mock_match_stats,
            icon_data_uri=get_placeholder_icon_data_uri(),
            past_ranks=[{"season": "Set 10", "rank": "Master"}, {"season": "Set 9", "rank": "Diamond I"}],
        )
        with open(OUTPUT_PATH, "w") as f:
            f.write(svg)
        print(f"preview card saved to {OUTPUT_PATH}")
        return

    game_name, tag_line = resolve_riot_id()
    riot_id_display = f"{game_name}#{tag_line}"
    print(f"Fetching stats for {riot_id_display} on {REGION}...")

    puuid = get_puuid(game_name, tag_line)
    print(f"  PUUID: {puuid[:12]}...")

    summoner = get_summoner_by_puuid(puuid)
    profile_icon_id = summoner.get("profileIconId", 1)
    print(f"  Profile Icon ID: {profile_icon_id}")

    icon_png_path = str(Path(OUTPUT_PATH).parent / "profile-icon.png")
    icon_data_uri = download_icon(profile_icon_id, save_path=icon_png_path)

    tier = os.environ.get("TFT_RANK_TIER", "")
    rank = os.environ.get("TFT_RANK_DIVISION", "")
    lp = int(os.environ.get("TFT_RANK_LP", "0"))
    if tier:
        print(f"  Rank (manual): {tier} {rank} - {lp} LP")
    else:
        tier = "UNRANKED"
        print("  No rank set")

    match_ids = get_match_ids(puuid, count=MATCH_COUNT)
    print(f"  Found {len(match_ids)} matches")

    match_stats = process_matches(puuid, match_ids)
    print(f"  Placements: {match_stats['placements']}")
    print(f"  Avg placement: {match_stats['avg_placement']:.2f}, Top 4: {match_stats['top4_rate']:.1f}%")

    past_ranks = [
        {"season": "Set 15", "rank": "Diamond IV"},
        {"season": "Set 14", "rank": "Diamond IV"},
        {"season": "Set 13", "rank": "Emerald IV"},
    ]

    svg = generate_svg(
        riot_id=riot_id_display, tier=tier, rank=rank, lp=lp,
        wins=match_stats["wins"],
        losses=match_stats["games_analyzed"] - match_stats["wins"],
        match_stats=match_stats, icon_data_uri=icon_data_uri, past_ranks=past_ranks,
    )

    with open(OUTPUT_PATH, "w") as f:
        f.write(svg)
    print(f"stats card saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()