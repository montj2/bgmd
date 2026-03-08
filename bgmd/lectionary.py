import icalendar
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Tuple
import re
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession
import asyncio
from urllib.parse import urlparse, parse_qs, unquote

class LectionaryProvider:
    ICS_URL = "http://lectionary.library.vanderbilt.edu/wp-content/uploads/feeds/daily.ics"
    
    def __init__(self, cache_dir: Optional[Path] = None):
        if cache_dir is None:
            self.cache_dir = Path.home() / ".cache" / "bgmd"
        else:
            self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ics_path = self.cache_dir / "lectionary.ics"

    async def _update_ics(self, force: bool = False):
        # Update if older than 24 hours
        if self.ics_path.exists() and not force:
            mtime = datetime.fromtimestamp(self.ics_path.stat().st_mtime)
            if (datetime.now() - mtime).days < 1:
                return

        async with AsyncSession(impersonate="chrome110") as session:
            resp = await session.get(self.ICS_URL)
            resp.raise_for_status()
            with open(self.ics_path, 'wb') as f:
                f.write(resp.content)

    def _parse_refs(self, description: str) -> List[str]:
        # Strip the URL part
        clean_desc = re.sub(r'\[http.*?\]', '', description).strip()
        # Split by semicolon
        refs = [r.strip() for r in clean_desc.split(';') if r.strip()]
        # Some special cases like "First Sunday of Advent" don't have refs in desc
        if len(refs) <= 1 and not re.search(r'\d', clean_desc):
            return []
        return refs

    async def get_readings(self, target_date: date) -> Tuple[str, List[str]]:
        await self._update_ics()
        
        with open(self.ics_path, 'rb') as f:
            cal = icalendar.Calendar.from_ical(f.read())

        for event in cal.walk('VEVENT'):
            dtstart = event.get('DTSTART').dt
            if isinstance(dtstart, datetime):
                dtstart = dtstart.date()
            
            if dtstart == target_date:
                summary = str(event.get('SUMMARY'))
                description = str(event.get('DESCRIPTION'))
                refs = self._parse_refs(description)
                
                if not refs:
                    url_match = re.search(r'(https?://lectionary\.library\.vanderbilt\.edu/texts/.*?)[\s\]]', description + " ")
                    if url_match:
                        url = url_match.group(1).strip()
                        refs = await self._scrape_vanderbilt(url)
                
                return summary, refs
        
        return "Unknown Day", []

    async def _scrape_vanderbilt(self, url: str) -> List[str]:
        safe_url = re.sub(r'\W+', '_', url)
        cache_path = self.cache_dir / "lectionary_pages" / f"{safe_url}.html"
        
        if cache_path.exists():
            with open(cache_path, 'r', encoding='utf-8') as f:
                html = f.read()
        else:
            async with AsyncSession(impersonate="chrome110") as session:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
                resp = await session.get(url, headers=headers)
                resp.raise_for_status()
                html = resp.text
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_path, 'w', encoding='utf-8') as f:
                    f.write(html)

        soup = BeautifulSoup(html, "lxml")
        refs = []
        
        # Look for BibleGateway links which contain the full list of references
        for a in soup.find_all('a', href=re.compile(r'biblegateway\.com/passage')):
            href = a.get('href')
            parsed_url = urlparse(href)
            query = parse_qs(parsed_url.query)
            if 'search' in query:
                search_val = query['search'][0]
                # If it's a semicolon separated list, it's our target
                if ';' in search_val:
                    raw_refs = search_val.split(';')
                    return [r.strip() for r in raw_refs if r.strip()]
        
        # Fallback to individual bibleref links
        for a in soup.select("a.bibleref"):
            ref = a.get_text().strip()
            if ref and ref not in refs:
                refs.append(ref)
        
        return refs

if __name__ == "__main__":
    async def test():
        provider = LectionaryProvider()
        d = date(2026, 3, 8)
        summary, refs = await provider.get_readings(d)
        print(f"Date: {d}")
        print(f"Summary: {summary}")
        print(f"Refs: {refs}")
    asyncio.run(test())
