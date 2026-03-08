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

    def __init__(self, translation: str = "NABRE", cache_dir: Optional[Path] = None):
        self.translation = translation
        self.base_url = "https://www.biblegateway.com/passage/"
        
        if cache_dir is None:
            self.cache_dir = Path.home() / ".cache" / "bgmd"
        else:
            self.cache_dir = cache_dir
            
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, book_bg_name: str, chapter: int, start_verse: Optional[int] = None, end_verse: Optional[int] = None) -> Path:
        # Sanitize name for filename
        safe_name = book_bg_name.replace("+", " ").replace(" ", "_").lower()
        filename = f"{safe_name}_{chapter}"
        if start_verse:
            filename += f"_{start_verse}"
            if end_verse and end_verse != start_verse:
                filename += f"-{end_verse}"
        filename += ".html"
        return self.cache_dir / self.translation.upper() / filename

    async def fetch_reference(
        self, 
        book_bg_name: str, 
        chapter: int, 
        start_verse: Optional[int] = None,
        end_verse: Optional[int] = None,
        use_cache: bool = True,
        randomize: bool = True,
        jitter: bool = True
    ) -> str:
        cache_path = self._get_cache_path(book_bg_name, chapter, start_verse, end_verse)
        
        if use_cache and cache_path.exists():
            with open(cache_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        full_chapter_path = self._get_cache_path(book_bg_name, chapter)
        if use_cache and full_chapter_path.exists():
            with open(full_chapter_path, 'r', encoding='utf-8') as f:
                return f.read()

        if jitter:
            await asyncio.sleep(random.uniform(0.5, 1.5))

        # IMPORTANT: Use space instead of + to ensure BibleGateway serves the SSR version
        search_ref = f"{book_bg_name.replace('+', ' ')} {chapter}"
        if start_verse:
            search_ref += f":{start_verse}"
            if end_verse and end_verse != start_verse:
                search_ref += f"-{end_verse}"

        params = {
            "search": search_ref,
            "version": self.translation,
            "interface": "print"
        }
        
        target = random.choice(self.IMPERSONATE_TARGETS) if randomize else "chrome110"
        
        async with AsyncSession(impersonate=target) as session:
            resp = await session.get(self.base_url, params=params, timeout=30)
            resp.raise_for_status()
            html = resp.text
            
            # Save to cache
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(html)
                
            return html

    async def fetch_chapter(self, book_bg_name: str, chapter: int, **kwargs) -> str:
        return await self.fetch_reference(book_bg_name, chapter, **kwargs)
