from bs4 import BeautifulSoup, Tag
from bgmd.models import PassageDoc, Verse, Footnote, CrossRef, SectionHeader
import re
import json

class Parser:
    def __init__(self, book: str, chapter: int, translation: str):
        self.book = book
        self.chapter = chapter
        self.translation = translation

    def parse(self, html: str) -> PassageDoc:
        soup = BeautifulSoup(html, "lxml")
        
        doc = PassageDoc(
            book=self.book,
            chapter=self.chapter,
            translation=self.translation
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
                    doc.footnotes.append(Footnote(label=label, text=text_span.get_text().strip()))

        current_verse_num = 0
        
        # SEARCH FOR ALL POTENTIAL VERSE SPANS
        # They either have an en- ID or a class like Book-Chapter-Verse
        pattern = rf"{self.book}-{self.chapter}-(\d+)"
        
        # Find all spans that have the verse class pattern or an en- ID
        all_spans = soup.find_all("span", class_=re.compile(r'text'))
        
        for span in all_spans:
            if any(cls in ['footer', 'nav', 'menu', 'sidebar'] for cls in [c for p in span.parents for c in p.get('class', []) if isinstance(c, str)]):
                continue

            v_num = None
            # 1. Check classes for Book-Chapter-Verse
            for cls in span.get('class', []):
                match = re.search(pattern, cls, re.IGNORECASE)
                if match:
                    v_num = int(match.group(1))
                    break
            
            # 2. Check for .versenum or .chapternum child
            if v_num is None:
                v_num_tag = span.select_one(".versenum, .chapternum")
                if v_num_tag:
                    num_match = re.search(r'(\d+)', v_num_tag.get_text())
                    if num_match:
                        v_num = int(num_match.group(1))
            
            # 3. Check ID as fallback
            if v_num is None:
                el_id = span.get('id', '')
                if el_id.startswith('en-'):
                    # We can't know the exact verse without more info, but usually 
                    # these spans are children of something we already found.
                    pass

            if v_num is not None:
                if not doc.verses or doc.verses[-1].number != v_num:
                    current_verse_num = v_num
                    doc.verses.append(Verse(number=v_num, text=""))
                
                # Extract text
                for node in span.children:
                    if isinstance(node, Tag):
                        classes = node.get('class', [])
                        if 'footnote' in classes:
                            doc.verses[-1].footnote_refs.append(node.get_text().strip('[]'))
                        elif 'crossreference' in classes:
                            doc.verses[-1].crossref_refs.append(node.get_text().strip('()'))
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

        # Final cleanup
        for v in doc.verses:
            v.text = re.sub(rf'^Chapter\s+{self.chapter}\s*', '', v.text, flags=re.IGNORECASE)
            v.text = re.sub(r'\s+', ' ', v.text).strip()
            v.text = re.sub(rf'^{v.number}\s*', '', v.text)
            v.text = v.text.replace('\xa0', ' ').strip()

        return doc
