import os
import requests
import re
from shadowcypher.core.logger import logger

class GamingAssetScraper:
    """Autonomous OSINT Scraper for Multi-Platform Asset Discovery. Handles Steam, Epic Games, GOG, and Prime Gaming."""
    
    def __init__(self):
        self.reddit_free_url = "https://www.reddit.com/r/FreeGameFindings/new/.json"
        self.local_library = set()
        
    def scan_local_library(self):
        """Scan Linux Steam paths for appmanifests."""
        paths = [
            os.path.expanduser("~/.steam/steam/steamapps/"),
            os.path.expanduser("~/.local/share/Steam/steamapps/"),
            "/usr/lib/steam/steamapps/"
        ]
        self.local_library = set()
        for p in paths:
            if os.path.exists(p):
                for f in os.listdir(p):
                    if f.endswith(".acf"):
                        match = re.search(r"appmanifest_(\d+)\.acf", f)
                        if match: self.local_library.add(match.group(1))
        return list(self.local_library)

    def fetch_global_assets(self):
        """Scrape global feeds and categorize by platform."""
        self.scan_local_library()
        categorized = {"Steam": [], "Epic": [], "GOG": [], "Other": []}
        
        try:
            headers = {'User-Agent': 'ShadowCypher-OSINT/2.0'}
            resp = requests.get(self.reddit_free_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for post in data['data']['children']:
                    item = post['data']
                    title = item['title']
                    url = item['url']
                    found_item = {"title": title, "url": url}
                    
                    if "[Steam]" in title:
                        id_match = re.search(r"app/(\d+)", url)
                        if id_match and id_match.group(1) in self.local_library: continue
                        categorized["Steam"].append(found_item)
                    elif "[Epic]" in title or "epicgames.com" in url:
                        categorized["Epic"].append(found_item)
                    elif "[GOG]" in title or "gog.com" in url:
                        categorized["GOG"].append(found_item)
                    else:
                        categorized["Other"].append(found_item)
        except Exception as e:
            logger.error("gaming_osint", f"Global Scrape Failed: {e}")
            
        return categorized

scraper = GamingAssetScraper()
