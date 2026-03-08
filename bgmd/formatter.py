from bgmd.models import PassageDoc

class Formatter:
    def __init__(self, mode: str = "obsidian"):
        self.mode = mode

    def format(self, doc: PassageDoc) -> str:
        if self.mode == "obsidian":
            return self._format_obsidian(doc)
        return self._format_plain(doc)

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
                    # Clean up refs like "a" or "1"
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
