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
                    # Also remove the verse reference link at the start if it exists
                    first_link = text_span.find("a", recursive=False)
                    if first_link and re.match(r'^\d', first_link.get_text()):
                        first_link.decompose()
                    doc.footnotes.append(Footnote(label=label, text=text_span.get_text().strip()))

        current_verse_num = 0
        # Strategy: Find all spans with IDs starting with 'en-'
        verse_elements = soup.find_all("span", id=re.compile(r'^en-'))
        
        for span in verse_elements:
            if any(cls in ['footer', 'nav', 'menu', 'sidebar'] for cls in [c for p in span.parents for c in p.get('class', []) if isinstance(c, str)]):
                continue

            v_num = None
            v_num_tag = span.select_one(".versenum, .chapternum")
            if v_num_tag:
                num_match = re.search(r'(\d+)', v_num_tag.get_text())
                if num_match:
                    v_num = int(num_match.group(1))
            
            if v_num is None:
                for cls in span.get('class', []):
                    # match pattern like John-3-16
                    match = re.search(rf"{self.book}-{self.chapter}-(\d+)", cls, re.IGNORECASE)
                    if match:
                        v_num = int(match.group(1))
                        break
            
            if v_num is not None:
                # FILTER: If we are parsing a full chapter but only want a range
                if self.start_verse and v_num < self.start_verse: continue
                if self.end_verse and v_num > self.end_verse: continue

                if not doc.verses or doc.verses[-1].number != v_num:
                    current_verse_num = v_num
                    doc.verses.append(Verse(number=v_num, text=""))
                
                # Extract text
                for node in span.children:
                    if isinstance(node, Tag):
                        classes = node.get('class', [])
                        if 'footnote' in classes:
                            fn_text = node.get_text().strip('[]')
                            doc.verses[-1].footnote_refs.append(fn_text)
                        elif 'crossreference' in classes:
                            cr_text = node.get_text().strip('()')
                            doc.verses[-1].crossref_refs.append(cr_text)
                        elif 'versenum' in classes or 'chapternum' in classes:
                            continue
                        elif 'inline-h3' in classes:
                            header_text = node.get_text().strip()
                            if not any(h.text == header_text for h in doc.section_headers):
                                doc.section_headers.append(SectionHeader(
                                    before_verse=current_verse_num,
                                    text=header_text
                                ))
                        else:
                            doc.verses[-1].text += node.get_text()
                    else:
                        doc.verses[-1].text += str(node)

        # Separate Header Extraction (if missed by inline check)
        for h in soup.find_all(['h3', 'h4', 'h5']):
            if 'chapter' in h.get('class', []): continue
            h_text = h.get_text().strip()
            if not any(sh.text == h_text for sh in doc.section_headers):
                # Hard to place without order, but we'll try
                doc.section_headers.append(SectionHeader(before_verse=1, text=h_text))

        # Final cleanup
        for v in doc.verses:
            v.text = re.sub(rf'^Chapter\s+{self.chapter}\s*', '', v.text, flags=re.IGNORECASE)
            v.text = re.sub(r'\s+', ' ', v.text).strip()
            v.text = re.sub(rf'^{v.number}\s*', '', v.text)
            v.text = v.text.replace('\xa0', ' ').strip()

        # Final Filter for Footnotes
        referenced_fns = set()
        for v in doc.verses:
            referenced_fns.update(v.footnote_refs)
        doc.footnotes = [fn for fn in doc.footnotes if fn.label in referenced_fns]

        return doc
