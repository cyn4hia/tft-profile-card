import os
import json
import ssl
import requests

ssl._create_default_https_context = ssl._create_unverified_context

API_KEY = os.environ.get("RIOT_API_KEY", "")

headers = {
    "X-Riot-Token": API_KEY,
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

# Test with Dishsoap (well-known NA TFT player)
print("=== 1. Get PUUID ===")
r = requests.get("https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/Dishsoap/NA1", headers=headers)
print(r.status_code, r.text[:200])
account = r.json()
puuid = account["puuid"]

print("\n=== 2. Get Summoner ===")
r = requests.get(f"https://na1.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}", headers=headers)
print(r.status_code, r.text[:300])
summoner = r.json()
print(f"Keys: {list(summoner.keys())}")

print("\n=== 3a. Ranked by PUUID ===")
r = requests.get(f"https://na1.api.riotgames.com/tft/league/v1/entries/by-puuid/{puuid}", headers=headers)
print(r.status_code, r.text[:500])

print("\n=== 3b. Ranked by summoner ID (if available) ===")
if "id" in summoner:
    r = requests.get(f"https://na1.api.riotgames.com/tft/league/v1/entries/by-summoner/{summoner['id']}", headers=headers)
    print(r.status_code, r.text[:500])
else:
    print("No summoner ID available")

print("\n=== 4. Match IDs ===")
r = requests.get(f"https://americas.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?count=5", headers=headers)
print(r.status_code, r.text[:300])


print("\n=== 5. Get Summoner ID via LoL Summoner-V4 ===")
r = requests.get(f"https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}", headers=headers)
print(r.status_code, r.text[:500])