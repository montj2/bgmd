import icalendar
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Tuple, Protocol
import re
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession
import asyncio
from urllib.parse import urlparse, parse_qs, unquote

class LectionaryProvider(Protocol):
    async def get_readings(self, target_date: date) -> Tuple[str, List[str]]:
        ...

class VanderbiltProvider:
    ICS_URL = "http://lectionary.library.vanderbilt.edu/wp-content/uploads/feeds/daily.ics"
    
    def __init__(self, cache_dir: Optional[Path] = None):
        if cache_dir is None:
            self.cache_dir = Path.home() / ".cache" / "bgmd"
        else:
            self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ics_path = self.cache_dir / "lectionary.ics"

    async def _update_ics(self, force: bool = False):
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
        clean_desc = re.sub(r'\[http.*?\]', '', description).strip()
        refs = [r.strip() for r in clean_desc.split(';') if r.strip()]
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
        for a in soup.find_all('a', href=re.compile(r'biblegateway\.com/passage')):
            href = a.get('href')
            query = parse_qs(urlparse(href).query)
            if 'search' in query:
                search_val = query['search'][0]
                if ';' in search_val:
                    return [r.strip() for r in search_val.split(';') if r.strip()]
        return [a.get_text().strip() for a in soup.select("a.bibleref")]

class USCCBProvider:
    def __init__(self, cache_dir: Optional[Path] = None):
        if cache_dir is None:
            self.cache_dir = Path.home() / ".cache" / "bgmd"
        else:
            self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def get_readings(self, target_date: date) -> Tuple[str, List[str]]:
        date_str = target_date.strftime("%m%d%y")
        url = f"https://bible.usccb.org/bible/readings/{date_str}.cfm"
        
        safe_url = re.sub(r'\W+', '_', url)
        cache_path = self.cache_dir / "lectionary_pages" / f"usccb_{safe_url}.html"
        
        html = ""
        if cache_path.exists():
            mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
            if (datetime.now() - mtime).days < 1:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    html = f.read()

        if not html:
            async with AsyncSession(impersonate="chrome110") as session:
                resp = await session.get(url)
                resp.raise_for_status()
                html = resp.text
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_path, 'w', encoding='utf-8') as f:
                    f.write(html)

        soup = BeautifulSoup(html, "lxml")
        summary = "Catholic Daily Readings"
        title_tag = soup.select_one(".content-header h1") or soup.select_one("title")
        if title_tag:
            summary = title_tag.get_text().strip().replace(" | USCCB", "")

        raw_refs = []
        for a in soup.find_all('a', href=re.compile(r'bible\.usccb\.org/bible/(?!readings)')):
            ref_text = a.get_text().strip()
            if ref_text and re.search(r'\d', ref_text) and not ref_text.startswith("http"):
                if ref_text not in raw_refs:
                    ref_text = ref_text.replace('\xa0', ' ')
                    if "See " in ref_text:
                        ref_text = ref_text.split("See ")[-1]
                    raw_refs.append(ref_text)
        
        # Post-process refs to handle multi-part ones like "Psalm 42:2, 3; 43:3, 4"
        final_refs = []
        for r in raw_refs:
            if ';' in r:
                # This is likely a multi-chapter reference. 
                # We need to split it but preserve the book name.
                parts = r.split(';')
                book_match = re.match(r'^([1-3]?\s*[a-zA-Z\s]+)', parts[0].strip())
                if book_match:
                    book_name = book_match.group(1).strip()
                    final_refs.append(parts[0].strip())
                    for p in parts[1:]:
                        p = p.strip()
                        # If the part doesn't start with a book name, prepend the previous one
                        if not re.match(r'^[1-3]?\s*[a-zA-Z]', p):
                            final_refs.append(f"{book_name} {p}")
                        else:
                            final_refs.append(p)
                else:
                    final_refs.append(r)
            else:
                final_refs.append(r)
                
        return summary, final_refs

def get_provider(source: str = "usccb", cache_dir: Optional[Path] = None) -> LectionaryProvider:
    if source.lower() == "vanderbilt":
        return VanderbiltProvider(cache_dir=cache_dir)
    return USCCBProvider(cache_dir=cache_dir)
