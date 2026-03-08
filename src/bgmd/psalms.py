from typing import Optional, Tuple, List

# Translations known to use the LXX/Vulgate Psalm numbering system
VULGATE_NUMBERED_VERSIONS = ["DRA", "VULGATE"]

def map_mt_to_vulgate(chapter: int, start_v: Optional[int] = None, end_v: Optional[int] = None) -> Tuple[int, Optional[int], Optional[int], str]:
    """
    Maps a Masoretic (Standard) Psalm reference to its Vulgate/LXX equivalent.
    Returns (new_chapter, new_start_v, new_end_v, note)
    """
    note = ""
    
    # 1-8: Identical
    if 1 <= chapter <= 8:
        return chapter, start_v, end_v, ""
    
    # 9-10: Combined into Ps 9 in Vulgate
    if chapter == 9:
        return 9, start_v, end_v, "Note: Combined into Ps 9 in Vulgate numbering."
    if chapter == 10:
        # MT 10 starts around LXX 9:22
        return 9, None, None, "Note: Psalm 10 (MT) is part of Psalm 9 in Vulgate. Verse mapping may vary."
    
    # 11-113: Offset by 1
    if 11 <= chapter <= 113:
        return chapter - 1, start_v, end_v, f"Mapping Psalm {chapter} -> {chapter-1} (Vulgate)"
    
    # 114-115: Combined into Ps 113 in Vulgate
    if chapter == 114:
        return 113, start_v, end_v, "Note: Combined into Ps 113 in Vulgate numbering."
    if chapter == 115:
        return 113, None, None, "Note: Psalm 115 (MT) is part of Psalm 113 in Vulgate. Verse mapping may vary."
    
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
