"""
generate cosmetics card svg
"""

import os
import base64
from pathlib import Path
from shared import *
from font import FREDOKA_FONT_FACE

CHIBI_COSMETICS = {
    "PetChibiLux": {
        "tactician_name": "Chibi Porcelain Lux",
        "arena": "Heaven's Celestial Court",
        "boom": "Porcelain Final Spark",
        "portal": "Porcelain Bloom",
        "arena_img": "cosmetics/koi-arena.png",
        "boom_img": "cosmetics/porcelain-boom.png",
        "portal_img": "cosmetics/porcelain-portal.png",
    },
}

COSMETICS_OUTPUT = os.environ.get("COSMETICS_OUTPUT", "tft-cosmetics.svg")


def get_companion_from_match(puuid, match_ids):
    if not match_ids:
        return None
    try:
        match = get_match_detail(match_ids[0])
        for p in match.get("info", {}).get("participants", []):
            if p.get("puuid") == puuid:
                return p.get("companion", {})
    except Exception as e:
        print(f"  could not get companion data: {e}", file=sys.stderr)
    return None


def get_tactician_image_uri(item_id):
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
        print(f"  could not fetch tactician image: {e}", file=sys.stderr)
    return ""


def generate_cosmetics_svg(companion, tactician_img_uri, cosmetics):
    species = companion.get("species", "Unknown")
    tactician_name = cosmetics.get("tactician_name", species.replace("PetChibi", "Chibi "))

    arena_uri = load_image_as_data_uri(cosmetics.get("arena_img", ""))
    boom_uri = load_image_as_data_uri(cosmetics.get("boom_img", ""))
    portal_uri = load_image_as_data_uri(cosmetics.get("portal_img", ""))

    card_w = 160
    card_h = 390

    def cosmetic_slot(y, label, name, img_uri):
        if img_uri:
            img_el = f'''
            <clipPath id="clip-{label.lower()}"><rect x="30" y="{y}" width="100" height="60" rx="8"/></clipPath>
            <rect x="30" y="{y}" width="100" height="60" rx="8" fill="#0d2137"/>
            <image href="{img_uri}" x="30" y="{y}" width="100" height="60" clip-path="url(#clip-{label.lower()})" preserveAspectRatio="xMidYMid slice" opacity="0.8"/>
            '''
        else:
            img_el = f'''
            <rect x="30" y="{y}" width="100" height="60" rx="8" fill="#0d2137" strokex="#1a3a5a" stroke-width="0.5" stroke-dasharray="3,2"/>
            <text x="80" y="{y + 23}" fill="#2a5a8a" font-size="8" font-family="'Fredoka', 'Segoe UI', sans-serif" text-anchor="middle">add image</text>
            '''
        return f'''
        <text x="80" y="{y - 5}" fill="#5a8ab5" font-size="8" font-family="'Fredoka', 'Segoe UI', sans-serif" font-weight="700" text-anchor="middle" letter-spacing="0.8">{escape_xml(label.upper())}</text>
        {img_el}
        <text x="80" y="{y + 70}" fill="#3d6d94" font-size="7" font-family="'Fredoka', 'Segoe UI', sans-serif" text-anchor="middle">{escape_xml(name)}</text>
        '''

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
        <text x="80" y="66" fill="#2a5a8a" font-size="9" font-family="'Fredoka', 'Segoe UI', sans-serif" text-anchor="middle">?</text>
        '''
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{card_w}" height="{card_h}" viewBox="0 0 {card_w} {card_h}" fill="none">

  {FREDOKA_FONT_FACE}

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

  <rect width="{card_w}" height="{card_h}" rx="16" fill="url(#cos-bg)"/>
  <rect width="{card_w}" height="{card_h}" rx="16" fill="none" stroke="url(#cos-border)" stroke-width="1.5"/>

  <rect x="30" y="0" width="100" height="2.5" rx="1.25" fill="#7ec8e3" opacity="0.4"/>

  <text x="80" y="22" fill="#7a9cc6" font-size="9" font-family="'Fredoka', 'Segoe UI', sans-serif" font-weight="700" text-anchor="middle" letter-spacing="1.5">✧ LOADOUT</text>

  {tact_img}
  <text x="80" y="104" fill="#d4e6f7" font-size="9" font-family="'Fredoka', 'Segoe UI', sans-serif" font-weight="700" text-anchor="middle">{escape_xml(tactician_name)}</text>

  {cosmetic_slot(125, "Arena", cosmetics.get("arena", ""), arena_uri)}
  {cosmetic_slot(217, "Boom", cosmetics.get("boom", ""), boom_uri)}
  {cosmetic_slot(310, "Portal", cosmetics.get("portal", ""), portal_uri)}


</svg>'''

    return svg


def main():
    if not RIOT_API_KEY and not PROXY_URL:
        print("No API key set, skipping cosmetics card")
        return

    game_name, tag_line = resolve_riot_id()
    print(f"Fetching cosmetics for {game_name}#{tag_line}...")

    puuid = get_puuid(game_name, tag_line)

    match_ids = get_match_ids(puuid, count=5)
    if not match_ids:
        print("  No matches found")
        return

    companion = get_companion_from_match(puuid, match_ids)
    if not companion:
        print("  could not detect companion")
        return

    species = companion.get("species", "")
    print(f"  Companion: {species} (item_ID: {companion.get('item_ID')})")

    cosmetics = CHIBI_COSMETICS.get(species, {})
    if not cosmetics:
        print(f"  no cosmetics mapping for {species} — add it to CHIBI_COSMETICS in generate_cosmetics.py")
        return

    tact_uri = get_tactician_image_uri(companion.get("item_ID", 0))
    if tact_uri:
        print(f"  fetched tactician image")
    else:
        print(f"  could not fetch tactician image")

    svg = generate_cosmetics_svg(companion, tact_uri, cosmetics)
    with open(COSMETICS_OUTPUT, "w") as f:
        f.write(svg)
    print(f"cosmetics card saved to {COSMETICS_OUTPUT}")


if __name__ == "__main__":
    main()