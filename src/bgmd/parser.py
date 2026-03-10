from bs4 import BeautifulSoup, Tag
from bgmd.models import PassageDoc, Verse, Footnote, CrossRef, SectionHeader
import re
import json
from typing import Optional, Set

class Parser:
    def __init__(
        self, 
        book: str, 
        chapter: int, 
        translation: str,
        start_verse: Optional[int] = None,
        end_verse: Optional[int] = None,
        requested_verses: Optional[Set[int]] = None
    ):
        self.book = book
        self.chapter = chapter
        self.translation = translation
        self.start_verse = start_verse
        self.end_verse = end_verse
        self.requested_verses = requested_verses

    def _get_verse_num(self, el: Tag) -> Optional[int]:
        # Helper to get the number from a specific tag
        v_text = el.get_text().strip()
        num_match = re.search(r'(\d+)', v_text)
        if num_match:
            val = int(num_match.group(1))
            if 'chapternum' in el.get('class', []):
                return 1
            return val
        return None

    def parse(self, html: str) -> PassageDoc:
        soup = BeautifulSoup(html, "lxml")
        
        doc = PassageDoc(
            book=self.book,
            chapter=self.chapter,
            translation=self.translation,
            start_verse=self.start_verse,
            end_verse=self.end_verse
        )

        # Extract Footnotes
        footnote_container = soup.select_one(".footnotes")
        if footnote_container:
            for fn_li in footnote_container.select("li"):
                fn_id = fn_li.get("id", "")
                label = fn_id.split("-")[-1]
                label = re.sub(r'^\d+', '', label)
                label_span = fn_li.select_one(".footnote-label")
                if label_span:
                    label = label_span.get_text().strip()
                text_span = fn_li.select_one(".footnote-text")
                if text_span:
                    for a in text_span.find_all("a", class_="backref"):
                        a.decompose()
                    first_link = text_span.find("a", recursive=False)
                    if first_link and re.match(r'^\d', first_link.get_text()):
                        first_link.decompose()
                    doc.footnotes.append(Footnote(label=label, text=text_span.get_text().strip()))

        container = soup.select_one(".passage-text") or soup.select_one(".passage-content") or soup
        
        current_verse_num = 0
        is_daniel_3 = self.book.lower() == "daniel" and self.chapter == 3
        highest_hebrew_verse = 0
        
        # We iterate over top-level blocks
        for el in container.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'span', 'b']):
            # Skip if nested inside another processed element
            if any(p.name == 'span' and 'text' in p.get('class', []) for p in el.parents):
                continue

            # Headers
            if el.name in ['h1', 'h2', 'h3', 'h4', 'h5'] or (el.name == 'b' and 'inline-h3' in el.get('class', [])):
                if 'chapter' in el.get('class', []): continue
                header_text = el.get_text().strip()
                if header_text:
                    doc.section_headers.append(SectionHeader(
                        before_verse=current_verse_num + 1,
                        text=header_text
                    ))
                continue

            # Verse Spans
            if el.name == 'span' and 'text' in el.get('class', []):
                # Process the content of the span, which might contain multiple verses
                for node in el.descendants:
                    # If we find a verse number marker
                    if isinstance(node, Tag) and ('versenum' in node.get('class', []) or 'chapternum' in node.get('class', [])):
                        v_num = self._get_verse_num(node)
                        if v_num is not None:
                            # Daniel 3 Heuristic
                            is_greek = False
                            if is_daniel_3:
                                if highest_hebrew_verse >= 23 and v_num < 90:
                                    is_greek = True
                                elif el.get('id') and 'Dan-3-' in str(el.get('class')):
                                    highest_hebrew_verse = max(highest_hebrew_verse, v_num)

                            # Handle Priority/Duplicates
                            existing = next((v for v in doc.verses if v.number == v_num), None)
                            if existing:
                                if is_greek:
                                    doc.verses.remove(existing)
                                else:
                                    # Already have it, skip
                                    continue

                            # Filter
                            if self.requested_verses:
                                if v_num not in self.requested_verses:
                                    current_verse_num = -1 # Signal skipping
                                    continue
                            else:
                                if self.start_verse and v_num < self.start_verse:
                                    current_verse_num = -1
                                    continue
                                if self.end_verse and v_num > self.end_verse:
                                    current_verse_num = -1
                                    continue

                            current_verse_num = v_num
                            doc.verses.append(Verse(number=v_num, text=""))
                    
                    elif isinstance(node, str):
                        # Text fragment
                        if current_verse_num > 0:
                            doc.verses[-1].text += node
                    
                    elif isinstance(node, Tag):
                        # Other content (footnotes, etc)
                        if current_verse_num > 0:
                            classes = node.get('class', [])
                            if 'footnote' in classes:
                                doc.verses[-1].footnote_refs.append(node.get_text().strip('[]'))
                            elif 'crossreference' in classes:
                                doc.verses[-1].crossref_refs.append(node.get_text().strip('()'))

        # Final cleanup
        for v in doc.verses:
            v.text = re.sub(rf'^Chapter\s+\d+\s*', '', v.text, flags=re.IGNORECASE)
            v.text = " ".join(v.text.split()).strip()
            # Remove leading verse number if it was duplicated in text
            v.text = re.sub(rf'^{v.number}\s*', '', v.text)
            v.text = v.text.replace('\xa0', ' ').strip()

        referenced_fns = set()
        for v in doc.verses:
            referenced_fns.update(v.footnote_refs)
        doc.footnotes = [fn for fn in doc.footnotes if fn.label in referenced_fns]

        return doc
