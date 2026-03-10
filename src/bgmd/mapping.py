from typing import Optional, Tuple, List, Set

# Translations known to use the LXX/Vulgate Psalm/Daniel numbering system
# Modern Catholic Bibles like NABRE use this for Daniel 3 additions.
VULGATE_STYLE_VERSIONS = ["DRA", "VULGATE", "NABRE"]

def map_mt_to_vulgate_psalm(chapter: int, start_v: Optional[int] = None, end_v: Optional[int] = None) -> Tuple[int, Optional[int], Optional[int], str]:
    """
    Maps a Masoretic (Standard) Psalm reference to its Vulgate/LXX equivalent.
    """
    # 1-8: Identical
    if 1 <= chapter <= 8:
        return chapter, start_v, end_v, ""
    
    # 9-10: Combined into Ps 9 in Vulgate
    if chapter == 9:
        return 9, start_v, end_v, "Note: Combined into Ps 9 in Vulgate numbering."
    if chapter == 10:
        return 9, None, None, "Note: Psalm 10 (MT) is part of Psalm 9 in Vulgate."
    
    # 11-113: Offset by 1
    if 11 <= chapter <= 113:
        return chapter - 1, start_v, end_v, f"Mapping Psalm {chapter} -> {chapter-1} (Vulgate)"
    
    # 114-115: Combined into Ps 113 in Vulgate
    if chapter == 114:
        return 113, start_v, end_v, "Note: Combined into Ps 113 in Vulgate numbering."
    if chapter == 115:
        return 113, None, None, "Note: Psalm 115 (MT) is part of Psalm 113 in Vulgate."
    
    # 116: Split into Ps 114 and 115 in Vulgate
    if chapter == 116:
        return 114, None, None, "Note: Psalm 116 (MT) is split into Ps 114 and 115 in Vulgate."
    
    # 117-146: Offset by 1
    if 117 <= chapter <= 146:
        return chapter - 1, start_v, end_v, f"Mapping Psalm {chapter} -> {chapter-1} (Vulgate)"
    
    # 147: Split into Ps 146 and 147 in Vulgate
    if chapter == 147:
        return 146, None, None, "Note: Psalm 147 (MT) is split into Ps 146 and 147 in Vulgate."
    
    # 148-150: Identical
    if 148 <= chapter <= 150:
        return chapter, start_v, end_v, ""
        
    return chapter, start_v, end_v, ""

def map_vulgate_to_mt_daniel(verses: Set[int]) -> Tuple[Set[int], str]:
    """
    Maps NABRE/Vulgate Daniel 3 numbering to MT/Hebrew numbering (used by RSVCE, ESV, etc).
    NABRE 24-90 are the Greek additions.
    NABRE 91-97 map to MT 24-30.
    """
    mapped = set()
    note = ""
    
    for v in verses:
        if v < 24:
            mapped.add(v)
        elif 24 <= v <= 90:
            # These are the Greek additions. In RSVCE, these are inside Chapter 3
            # but labeled with their own numbering starting from 1.
            # Offset is 23 (24 -> 1, 25 -> 2).
            mapped.add(v - 23)
            note = "Note: Mapping Daniel 3 Greek additions to translation's internal numbering."
        elif v >= 91:
            # Shift back to Hebrew story
            # 91 -> 24, 92 -> 25. Offset is 67.
            mapped.add(v - 67)
            
    return mapped, note

def map_reference(
    book_slug: str, 
    chapter: int, 
    verses: Set[int], 
    translation: str, 
    is_usccb: bool = False
) -> Tuple[int, Set[int], str]:
    """
    Unified entry point for reference mapping.
    Returns (actual_chapter, actual_verses, note)
    """
    translation = translation.upper()
    
    # CASE 1: Psalm Mapping (Standard -> Vulgate)
    if book_slug == "psalms" and translation in ["DRA", "VULGATE"]:
        start_v = min(verses) if verses else None
        end_v = max(verses) if verses else None
        ch, s, e, note = map_mt_to_vulgate_psalm(chapter, start_v, end_v)
        new_verses = set(range(s, e + 1)) if s and e else set()
        return ch, new_verses, note

    # CASE 2: Daniel 3 Mapping (USCCB/NABRE -> Standard/MT)
    # Triggered if source is USCCB and translation uses MT numbering (RSVCE, ESV, etc)
    if is_usccb and book_slug == "daniel" and chapter == 3:
        if translation not in VULGATE_STYLE_VERSIONS:
            new_verses, note = map_vulgate_to_mt_daniel(verses)
            return chapter, new_verses, note
            
    return chapter, verses, ""
