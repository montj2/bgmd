from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Verse:
    number: int
    text: str
    footnote_refs: list[str] = field(default_factory=list)
    crossref_refs: list[str] = field(default_factory=list)

@dataclass
class Footnote:
    label: str
    text: str

@dataclass
class CrossRef:
    label: str
    targets: list[str] = field(default_factory=list)

@dataclass
class SectionHeader:
    before_verse: int
    text: str

@dataclass
class PassageDoc:
    book: str
    chapter: int
    translation: str
    start_verse: Optional[int] = None
    end_verse: Optional[int] = None
    verses: list[Verse] = field(default_factory=list)
    section_headers: list[SectionHeader] = field(default_factory=list)
    footnotes: list[Footnote] = field(default_factory=list)
    crossrefs: list[CrossRef] = field(default_factory=list)
    copyright: str = ""
    prev: str | None = None
    next: str | None = None

    @property
    def reference(self) -> str:
        ref = f"{self.book} {self.chapter}"
        if self.start_verse:
            ref += f":{self.start_verse}"
            if self.end_verse and self.end_verse != self.start_verse:
                ref += f"-{self.end_verse}"
        return ref
