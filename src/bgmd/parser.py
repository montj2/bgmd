from bs4 import BeautifulSoup, Tag
from bgmd.models import PassageDoc, Verse, Footnote, CrossRef, SectionHeader
import re
import json
from typing import Optional

class Parser:
    def __init__(
        self, 
        book: str, 
        chapter: int, 
        translation: str,
        start_verse: Optional[int] = None,
        end_verse: Optional[int] = None
    ):
        self.book = book
        self.chapter = chapter
        self.translation = translation
        self.start_verse = start_verse
        self.end_verse = end_verse

    def _get_verse_num(self, el: Tag) -> Optional[int]:
        # 1. Check for .versenum or .chapternum child
        v_num_tag = el.select_one(".versenum, .chapternum")
        if v_num_tag:
            v_text = v_num_tag.get_text().strip()
            num_match = re.search(r'(\d+)', v_text)
            if num_match:
                val = int(num_match.group(1))
                if 'chapternum' in v_num_tag.get('class', []):
                    # HEURISTIC: In most cases, a chapternum at the start of a passage
                    # is verse 1. This is true even if we've mapped the chapter.
                    return 1
                return val
        
        # 2. Check classes for Book-Chapter-Verse
        for cls in el.get('class', []):
            match = re.search(rf"-(\d+)$", cls)
            if match:
                return int(match.group(1))
            
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
        for el in container.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'span', 'b']):
            if any(p.name in ['h1', 'h2', 'h3', 'h4', 'h5'] for p in el.parents):
                continue
            if any(p.name == 'span' and 'text' in p.get('class', []) for p in el.parents):
                continue

            if el.name in ['h1', 'h2', 'h3', 'h4', 'h5'] or (el.name == 'b' and 'inline-h3' in el.get('class', [])):
                if 'chapter' in el.get('class', []): continue
                header_text = el.get_text().strip()
                if header_text:
                    doc.section_headers.append(SectionHeader(
                        before_verse=current_verse_num + 1,
                        text=header_text
                    ))
                continue

            if el.name == 'span' and 'text' in el.get('class', []):
                v_num = self._get_verse_num(el)
                
                if v_num is not None:
                    if self.start_verse and v_num < self.start_verse: continue
                    if self.end_verse and v_num > self.end_verse: continue

                    if not doc.verses or doc.verses[-1].number != v_num:
                        current_verse_num = v_num
                        doc.verses.append(Verse(number=v_num, text=""))
                    
                    clean_text = ""
                    for node in el.children:
                        if isinstance(node, Tag):
                            classes = node.get('class', [])
                            if 'footnote' in classes:
                                doc.verses[-1].footnote_refs.append(node.get_text().strip('[]'))
                            elif 'crossreference' in classes:
                                doc.verses[-1].crossref_refs.append(node.get_text().strip('()'))
                            elif 'versenum' in classes or 'chapternum' in classes:
                                continue
                            elif 'inline-h3' in classes:
                                h_text = node.get_text().strip()
                                if h_text and not any(sh.text == h_text for h in doc.section_headers):
                                    doc.section_headers.append(SectionHeader(
                                        before_verse=current_verse_num,
                                        text=h_text
                                    ))
                            else:
                                clean_text += node.get_text()
                        else:
                            clean_text += str(node)
                    
                    doc.verses[-1].text += " " + clean_text

        for v in doc.verses:
            v.text = re.sub(rf'^Chapter\s+\d+\s*', '', v.text, flags=re.IGNORECASE)
            # STRIP ALL NEWLINES AND TABS
            v.text = " ".join(v.text.split()).strip()
            # Special case for verse 1: BibleGateway often includes the chapter number
            # in the text of verse 1. We strip it if it looks like a chapter prefix.
            v.text = re.sub(r'^\d+\s+', '', v.text)
            v.text = re.sub(rf'^{v.number}\s*', '', v.text)
            v.text = v.text.replace('\xa0', ' ').strip()

        referenced_fns = set()
        for v in doc.verses:
            referenced_fns.update(v.footnote_refs)
        doc.footnotes = [fn for fn in doc.footnotes if fn.label in referenced_fns]

        return doc
