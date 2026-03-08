from bgmd.models import PassageDoc, ComparisonDoc
from typing import List, Dict
import re

class Formatter:
    def __init__(self, mode: str = "obsidian"):
        self.mode = mode

    def format(self, doc: PassageDoc) -> str:
        if self.mode == "obsidian":
            return self._format_obsidian(doc)
        return self._format_plain(doc)

    def format_comparison(self, comp: ComparisonDoc, layout: str = "table") -> str:
        if layout == "table":
            return self._format_comparison_table(comp)
        return self._format_comparison_interleaved(comp)

    def _format_comparison_table(self, comp: ComparisonDoc) -> str:
        lines = [f"# Comparison: {comp.reference}", ""]
        
        # Header row
        header = "| Verse | " + " | ".join(comp.translations) + " |"
        sep = "| :--- | " + " | ".join([":---"] * len(comp.translations)) + " |"
        lines.append(header)
        lines.append(sep)
        
        # Get all verse numbers across all docs
        all_nums = set()
        for doc in comp.docs:
            all_nums.update(v.number for v in doc.verses)
        
        for v_num in sorted(all_nums):
            row_parts = [f" {v_num} "]
            for doc in comp.docs:
                v = next((v for v in doc.verses if v.number == v_num), None)
                text = v.text if v else "_"
                
                # NORMALIZE EVERYTHING
                # 1. Replace all whitespace types with a single space
                text = " ".join(text.split())
                # 2. Escape pipes
                text = text.replace("|", "\\|")
                row_parts.append(f" {text} ")
            
            row = "|" + "|".join(row_parts) + "|"
            lines.append(row)
            
        return "\n".join(lines)

    def _format_comparison_interleaved(self, comp: ComparisonDoc) -> str:
        lines = [f"# Comparison: {comp.reference}", ""]
        
        all_nums = set()
        for doc in comp.docs:
            all_nums.update(v.number for v in doc.verses)
            
        for v_num in sorted(all_nums):
            lines.append(f"### Verse {v_num}")
            for doc in comp.docs:
                v = next((v for v in doc.verses if v.number == v_num), None)
                if v:
                    lines.append(f"**{doc.translation}**: {v.text}")
            lines.append("")
            
        return "\n".join(lines)

    def _format_obsidian(self, doc: PassageDoc) -> str:
        lines = []
        
        # Front matter
        lines.append("---")
        lines.append(f"book: {doc.book}")
        lines.append(f"chapter: {doc.chapter}")
        if doc.start_verse:
            lines.append(f"start_verse: {doc.start_verse}")
            if doc.end_verse:
                lines.append(f"end_verse: {doc.end_verse}")
        lines.append(f"reference: \"{doc.reference}\"")
        lines.append(f"translation: {doc.translation}")
        if doc.prev or doc.next:
            if doc.prev:
                lines.append(f"prev: \"[[{doc.prev}]]\"")
            if doc.next:
                lines.append(f"next: \"[[{doc.next}]]\"")
        lines.append("---")
        lines.append("")
        
        # Title
        lines.append(f"# {doc.reference}")
        lines.append("")
        
        # Verses and Headers
        verse_map = {v.number: v for v in doc.verses}
        header_map = {h.before_verse: h for h in doc.section_headers}
        
        all_verse_nums = sorted(verse_map.keys())
        if not all_verse_nums:
            return "\n".join(lines)
        
        for v_num in range(min(all_verse_nums), max(all_verse_nums) + 1):
            if v_num in header_map:
                lines.append(f"## {header_map[v_num].text}")
                lines.append("")
            
            if v_num in verse_map:
                verse = verse_map[v_num]
                text = verse.text
                
                # Add inline footnotes if applicable
                for fn_ref in verse.footnote_refs:
                    text += f"^[{fn_ref}]"
                
                lines.append(f"###### {v_num}")
                lines.append(text)
                lines.append("")

        # Footnotes Section
        if doc.footnotes:
            lines.append("---")
            lines.append("")
            lines.append("## Footnotes")
            lines.append("")
            for fn in doc.footnotes:
                lines.append(f"**{fn.label}.** {fn.text}")
            lines.append("")

        # Cross-References Section
        if doc.crossrefs:
            if not doc.footnotes:
                lines.append("---")
                lines.append("")
            lines.append("## Cross-References")
            lines.append("")
            for cr in doc.crossrefs:
                targets_str = ", ".join(cr.targets)
                lines.append(f"**{cr.label}.** {targets_str}")
            lines.append("")

        return "\n".join(lines)

    def _format_plain(self, doc: PassageDoc) -> str:
        lines = [f"# {doc.reference}", ""]
        for v in doc.verses:
            lines.append(f"**{v.number}** {v.text}")
            lines.append("")
        return "\n".join(lines)
