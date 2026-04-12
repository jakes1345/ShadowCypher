"""
ShadowCypher Gaming OSINT Engine — Multi-Platform Asset Discovery.

Features:
- Steam library sync (local .acf manifests + API)
- Steam Web API integration (owned games, player profile, wishlist)
- Live deal tracking (Steam featured specials, free games)
- Multi-platform free game discovery (Reddit, Epic, GOG)
- Steam Store deep search
- Game price history via IsThereAnyDeal
"""

import os
import re
import json
import time
import threading
import requests
from pathlib import Path
from shadowcypher.core.logger import logger
from shadowcypher.core.platform import platform_engine
from shadowcypher.core.config import config


class GamingAssetScraper:
    """Autonomous OSINT Scraper for Multi-Platform Asset Discovery.
    Handles Steam, Epic Games, GOG, and Prime Gaming."""

    STEAM_API_BASE = "https://api.steampowered.com"
    STEAM_STORE_BASE = "https://store.steampowered.com"
    REDDIT_FREE_URL = "https://www.reddit.com/r/FreeGameFindings/new/.json"
    ITAD_API_BASE = "https://api.isthereanydeal.com"

    def __init__(self):
        self.local_library = set()
        self.local_library_details = {}
        self.steam_api_key = os.environ.get("STEAM_API_KEY", "")
        self.steam_id = os.environ.get("STEAM_ID", "")
        self.itad_key = os.environ.get("ITAD_API_KEY", "")
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "ShadowCypher-OSINT/3.0 (Gaming Asset Discovery Engine)"
        })
        self._cache = {}
        self._cache_ttl = 300  # 5 minute cache

    # ══════════════════════════════════════════════════
    # ── Configuration ──
    # ══════════════════════════════════════════════════

    def set_credentials(self, steam_api_key="", steam_id="", itad_key=""):
        """Set API credentials at runtime."""
        if steam_api_key:
            self.steam_api_key = steam_api_key
        if steam_id:
            self.steam_id = steam_id
        if itad_key:
            self.itad_key = itad_key

    @property
    def is_authenticated(self):
        return bool(self.steam_api_key and self.steam_id)

    # ══════════════════════════════════════════════════
    # ── Local Library Scanning ──
    # ══════════════════════════════════════════════════

    def scan_local_library(self):
        """Scan local Steam installations for installed games via .acf manifests."""
        search_paths = []

        if platform_engine.IS_LINUX:
            search_paths = [
                os.path.expanduser("~/.steam/steam/steamapps/"),
                os.path.expanduser("~/.local/share/Steam/steamapps/"),
                "/usr/lib/steam/steamapps/",
            ]
        elif platform_engine.IS_MACOS:
            search_paths = [
                os.path.expanduser("~/Library/Application Support/Steam/steamapps/"),
            ]
        elif platform_engine.IS_WINDOWS:
            search_paths = [
                "C:\\Program Files (x86)\\Steam\\steamapps\\",
                "C:\\Program Files\\Steam\\steamapps\\",
            ]

        # Also check libraryfolders.vdf for extra Steam libraries
        for base in list(search_paths):
            vdf_path = os.path.join(base, "libraryfolders.vdf")
            if os.path.exists(vdf_path):
                try:
                    with open(vdf_path) as f:
                        content = f.read()
                    extra_paths = re.findall(r'"path"\s+"([^"]+)"', content)
                    for ep in extra_paths:
                        steamapps = os.path.join(ep, "steamapps")
                        if os.path.isdir(steamapps) and steamapps not in search_paths:
                            search_paths.append(steamapps)
                except Exception:
                    pass

        self.local_library = set()
        self.local_library_details = {}

        for steam_dir in search_paths:
            if not os.path.isdir(steam_dir):
                continue
            for fname in os.listdir(steam_dir):
                if not fname.startswith("appmanifest_") or not fname.endswith(".acf"):
                    continue
                match = re.search(r"appmanifest_(\d+)\.acf", fname)
                if not match:
                    continue
                app_id = match.group(1)
                self.local_library.add(app_id)

                # Parse ACF for game name and install size
                try:
                    acf_path = os.path.join(steam_dir, fname)
                    with open(acf_path) as f:
                        acf = f.read()
                    name_match = re.search(r'"name"\s+"([^"]+)"', acf)
                    size_match = re.search(r'"SizeOnDisk"\s+"(\d+)"', acf)
                    state_match = re.search(r'"StateFlags"\s+"(\d+)"', acf)

                    self.local_library_details[app_id] = {
                        "name": name_match.group(1) if name_match else f"App {app_id}",
                        "size_bytes": int(size_match.group(1)) if size_match else 0,
                        "state": int(state_match.group(1)) if state_match else 0,
                        "path": steam_dir,
                    }
                except Exception:
                    self.local_library_details[app_id] = {
                        "name": f"App {app_id}", "size_bytes": 0, "state": 0, "path": steam_dir
                    }

        logger.info("gaming", f"LOCAL_LIBRARY_SYNC: {len(self.local_library)} games found")
        return list(self.local_library)

    def get_local_library_summary(self):
        """Get a formatted summary of the local Steam library."""
        if not self.local_library_details:
            self.scan_local_library()

        total_size = sum(d["size_bytes"] for d in self.local_library_details.values())
        size_gb = total_size / (1024 ** 3)

        games = sorted(
            self.local_library_details.items(),
            key=lambda x: x[1]["size_bytes"],
            reverse=True
        )

        return {
            "total_games": len(games),
            "total_size_gb": round(size_gb, 2),
            "games": [
                {
                    "app_id": aid,
                    "name": info["name"],
                    "size_gb": round(info["size_bytes"] / (1024 ** 3), 2),
                    "installed": info["state"] == 4,
                }
                for aid, info in games
            ]
        }

    # ══════════════════════════════════════════════════
    # ── Steam Web API Integration ──
    # ══════════════════════════════════════════════════

    def _steam_api(self, endpoint, params=None):
        """Make an authenticated Steam Web API call."""
        if not self.steam_api_key:
            return {"error": "NO_API_KEY — Set STEAM_API_KEY env var or use Settings"}
        p = params or {}
        p["key"] = self.steam_api_key
        try:
            r = self._session.get(f"{self.STEAM_API_BASE}/{endpoint}", params=p, timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("gaming", f"Steam API error: {e}")
            return {"error": str(e)}

    def get_owned_games(self, steam_id=None):
        """Get full library of owned games from Steam API."""
        sid = steam_id or self.steam_id
        if not sid:
            return {"error": "NO_STEAM_ID — Set STEAM_ID env var or use Settings"}
        data = self._steam_api("IPlayerService/GetOwnedGames/v1/", {
            "steamid": sid,
            "include_appinfo": "true",
            "include_played_free_games": "true",
        })
        response = data.get("response", {})
        games = response.get("games", [])
        return {
            "total": response.get("game_count", len(games)),
            "games": sorted(games, key=lambda g: g.get("playtime_forever", 0), reverse=True),
        }

    def get_player_profile(self, steam_id=None):
        """Get player profile summary."""
        sid = steam_id or self.steam_id
        if not sid:
            return {"error": "NO_STEAM_ID"}
        data = self._steam_api("ISteamUser/GetPlayerSummaries/v2/", {"steamids": sid})
        players = data.get("response", {}).get("players", [])
        return players[0] if players else {"error": "PROFILE_NOT_FOUND"}

    def get_recently_played(self, steam_id=None, count=10):
        """Get recently played games."""
        sid = steam_id or self.steam_id
        if not sid:
            return {"error": "NO_STEAM_ID"}
        data = self._steam_api("IPlayerService/GetRecentlyPlayedGames/v1/", {
            "steamid": sid, "count": str(count)
        })
        return data.get("response", {}).get("games", [])

    def get_friend_list(self, steam_id=None):
        """Get friend list."""
        sid = steam_id or self.steam_id
        if not sid:
            return {"error": "NO_STEAM_ID"}
        data = self._steam_api("ISteamUser/GetFriendList/v1/", {
            "steamid": sid, "relationship": "friend"
        })
        return data.get("friendslist", {}).get("friends", [])

    # ══════════════════════════════════════════════════
    # ── Steam Store API (No API Key Needed) ──
    # ══════════════════════════════════════════════════

    def _cached_get(self, url, key, ttl=None):
        """GET with in-memory caching."""
        ttl = ttl or self._cache_ttl
        now = time.time()
        if key in self._cache and (now - self._cache[key]["ts"]) < ttl:
            return self._cache[key]["data"]
        try:
            r = self._session.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()
            self._cache[key] = {"data": data, "ts": now}
            return data
        except Exception as e:
            logger.error("gaming", f"Store API error [{key}]: {e}")
            return {}

    def get_featured_deals(self):
        """Get featured games with discounts from Steam store."""
        data = self._cached_get(
            f"{self.STEAM_STORE_BASE}/api/featuredcategories",
            "featured_cats"
        )
        result = {"specials": [], "top_sellers": [], "new_releases": [], "coming_soon": []}

        for category in ["specials", "top_sellers", "new_releases", "coming_soon"]:
            items = data.get(category, {}).get("items", [])
            for item in items:
                result[category].append({
                    "app_id": str(item.get("id", "")),
                    "name": item.get("name", "Unknown"),
                    "discount_pct": item.get("discount_percent", 0),
                    "original_price": (item.get("original_price") or 0) / 100,
                    "final_price": (item.get("final_price") or 0) / 100,
                    "currency": item.get("currency", "USD"),
                    "header_image": item.get("header_image", ""),
                    "linux": item.get("linux_available", False),
                    "windows": item.get("windows_available", True),
                    "mac": item.get("mac_available", False),
                    "already_owned": str(item.get("id", "")) in self.local_library,
                })

        logger.info("gaming", f"DEALS_FETCHED: {sum(len(v) for v in result.values())} items")
        return result

    def get_app_details(self, app_id):
        """Get full details for a specific Steam app."""
        data = self._cached_get(
            f"{self.STEAM_STORE_BASE}/api/appdetails?appids={app_id}",
            f"app_{app_id}",
            ttl=600
        )
        return data.get(str(app_id), {}).get("data", {})

    def search_store(self, term, max_results=25):
        """Search the Steam store."""
        try:
            r = self._session.get(
                f"{self.STEAM_STORE_BASE}/api/storesearch/",
                params={"term": term, "l": "english", "cc": "us"},
                timeout=15
            )
            r.raise_for_status()
            data = r.json()
            items = data.get("items", [])[:max_results]
            return [{
                "app_id": str(item.get("id", "")),
                "name": item.get("name", ""),
                "price": item.get("price", {}),
                "tiny_image": item.get("tiny_image", ""),
                "linux": item.get("platforms", {}).get("linux", False),
            } for item in items]
        except Exception as e:
            logger.error("gaming", f"Store search error: {e}")
            return []

    def find_free_games_steam(self):
        """Find currently free-to-keep promotions on Steam (100% discount)."""
        deals = self.get_featured_deals()
        free = []
        for item in deals.get("specials", []):
            if item["discount_pct"] == 100 and not item["already_owned"]:
                free.append(item)
        return free

    # ══════════════════════════════════════════════════
    # ── Multi-Platform Free Game Discovery ──
    # ══════════════════════════════════════════════════

    def fetch_global_assets(self):
        """Scrape global feeds and categorize by platform."""
        self.scan_local_library()
        categorized = {"Steam": [], "Epic": [], "GOG": [], "Prime": [], "Other": []}

        # 1. Reddit r/FreeGameFindings
        try:
            resp = self._session.get(self.REDDIT_FREE_URL, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for post in data.get("data", {}).get("children", []):
                    item = post["data"]
                    title = item.get("title", "")
                    url = item.get("url", "")
                    score = item.get("score", 0)
                    flair = item.get("link_flair_text", "")

                    found = {
                        "title": title,
                        "url": url,
                        "score": score,
                        "flair": flair,
                        "source": "reddit",
                    }

                    title_lower = title.lower()
                    if "[steam]" in title_lower or "store.steampowered.com" in url:
                        id_match = re.search(r"app/(\d+)", url)
                        if id_match and id_match.group(1) in self.local_library:
                            found["already_owned"] = True
                        categorized["Steam"].append(found)
                    elif "[epic" in title_lower or "epicgames.com" in url:
                        categorized["Epic"].append(found)
                    elif "[gog" in title_lower or "gog.com" in url:
                        categorized["GOG"].append(found)
                    elif "[prime" in title_lower or "amazon" in title_lower:
                        categorized["Prime"].append(found)
                    else:
                        categorized["Other"].append(found)
        except Exception as e:
            logger.error("gaming", f"Reddit scrape failed: {e}")

        # 2. Steam featured free games (100% off specials)
        try:
            steam_free = self.find_free_games_steam()
            for item in steam_free:
                if not any(f["title"] == item["name"] for f in categorized["Steam"]):
                    categorized["Steam"].insert(0, {
                        "title": f"🎁 FREE: {item['name']}",
                        "url": f"https://store.steampowered.com/app/{item['app_id']}",
                        "score": 9999,
                        "source": "steam_store",
                        "original_price": item["original_price"],
                    })
        except Exception as e:
            logger.error("gaming", f"Steam free scan failed: {e}")

        total = sum(len(v) for v in categorized.values())
        logger.info("gaming", f"GLOBAL_DISCOVERY: {total} free assets found")
        return categorized

    # ══════════════════════════════════════════════════
    # ── Wishlist & Deal Sniping ──
    # ══════════════════════════════════════════════════

    def get_wishlist(self, steam_id=None):
        """Get a user's Steam wishlist (public profiles only)."""
        sid = steam_id or self.steam_id
        if not sid:
            return {"error": "NO_STEAM_ID"}
        try:
            # Steam wishlist is paginated
            all_items = {}
            page = 0
            while True:
                r = self._session.get(
                    f"{self.STEAM_STORE_BASE}/wishlist/profiles/{sid}/wishlistdata/",
                    params={"p": page},
                    timeout=15
                )
                if r.status_code != 200:
                    break
                data = r.json()
                if not data:
                    break
                all_items.update(data)
                page += 1
                if page > 10:  # Safety limit
                    break

            wishlist = []
            for app_id, info in all_items.items():
                is_free = info.get("is_free_game", False)
                subs = info.get("subs", [])
                best_price = None
                best_discount = 0
                for sub in subs:
                    discount = sub.get("discount_pct", 0)
                    if discount >= best_discount:
                        best_discount = discount
                        best_price = (sub.get("price") or 0) / 100

                wishlist.append({
                    "app_id": app_id,
                    "name": info.get("name", f"App {app_id}"),
                    "priority": info.get("priority", 99),
                    "is_free": is_free,
                    "on_sale": best_discount > 0,
                    "discount_pct": best_discount,
                    "sale_price": best_price,
                    "review_score": info.get("review_score", 0),
                    "release_date": info.get("release_string", ""),
                    "already_owned": app_id in self.local_library,
                })

            wishlist.sort(key=lambda x: (-x["discount_pct"], x["priority"]))
            return wishlist
        except Exception as e:
            logger.error("gaming", f"Wishlist fetch error: {e}")
            return {"error": str(e)}

    def snipe_wishlist_deals(self, steam_id=None):
        """Find games on your wishlist that are currently on sale."""
        wishlist = self.get_wishlist(steam_id)
        if isinstance(wishlist, dict) and "error" in wishlist:
            return wishlist
        return [g for g in wishlist if g["on_sale"] and not g["already_owned"]]


# Global singleton
scraper = GamingAssetScraper()
