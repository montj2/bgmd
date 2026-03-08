from curl_cffi.requests import AsyncSession
import asyncio
import os
import random
from pathlib import Path
from typing import Optional

class Fetcher:
    # Stable impersonation profiles for randomization
    IMPERSONATE_TARGETS = [
        "chrome110", "chrome116", "chrome119", "chrome120",
        "edge101", "safari15_5", "safari17_0",
        "firefox133"
    ]

    def __init__(self, translation: str = "NABRE", cache_dir: str = ".bgmd_cache"):
        self.translation = translation
        self.base_url = "https://www.biblegateway.com/passage/"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, book_bg_name: str, chapter: int) -> Path:
        safe_name = book_bg_name.replace("+", "_").lower()
        return self.cache_dir / self.translation.upper() / f"{safe_name}_{chapter}.html"

    async def fetch_chapter(
        self, 
        book_bg_name: str, 
        chapter: int, 
        use_cache: bool = True,
        randomize: bool = True,
        jitter: bool = True
    ) -> str:
        cache_path = self._get_cache_path(book_bg_name, chapter)
        
        if use_cache and cache_path.exists():
            with open(cache_path, 'r', encoding='utf-8') as f:
                return f.read()

        # Add jitter to avoid bursty behavior
        if jitter:
            delay = random.uniform(0.5, 2.0)
            await asyncio.sleep(delay)

        search_ref = f"{book_bg_name}+{chapter}"
        params = {
            "search": search_ref,
            "version": self.translation,
            "interface": "print"
        }
        
        # Select randomization target
        target = "chrome110" # Default
        if randomize:
            target = random.choice(self.IMPERSONATE_TARGETS)
        
        async with AsyncSession(impersonate=target) as session:
            resp = await session.get(self.base_url, params=params, timeout=30)
            resp.raise_for_status()
            html = resp.text
            
            # Save to cache
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(html)
                
            return html

if __name__ == "__main__":
    async def test():
        fetcher = Fetcher()
        print("Testing randomized fetch...")
        html = await fetcher.fetch_chapter("John", 3, use_cache=False, randomize=True)
        print(f"Fetched John 3 (length: {len(html)})")
    asyncio.run(test())
