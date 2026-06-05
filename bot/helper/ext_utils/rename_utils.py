import re
from os import path as ospath
from bot.helper.ext_utils.media_utils import get_media_info
from bot.helper.ext_utils.metadata_utils import MetadataProcessor
from bot import LOGGER, user_data

SEASON_EPISODE_PATTERNS = [
    # Standard patterns (S01E02, S01EP02)
    (re.compile(r'S(\d+)(?:E|EP)(\d+)'), ('season', 'episode')),
    # Patterns with spaces/dashes (S01 E02, S01-EP02)
    (re.compile(r'S(\d+)[\s-]*(?:E|EP)(\d+)'), ('season', 'episode')),
    # Full text patterns (Season 1 Episode 2)
    (re.compile(r'Season\s*(\d+)\s*Episode\s*(\d+)', re.IGNORECASE), ('season', 'episode')),
    # Patterns with brackets/parentheses ([S01][E02])
    (re.compile(r'\[S(\d+)\]\[E(\d+)\]'), ('season', 'episode')),
    # Fallback patterns (S01 13, Episode 13)
    (re.compile(r'S(\d+)[^\d]*(\d+)'), ('season', 'episode')),
    (re.compile(r'(?:E|EP|Episode)\s*(\d+)', re.IGNORECASE), (None, 'episode')),
    # Final fallback (standalone number)
    (re.compile(r'\b(\d+)\b'), (None, 'episode'))
]

# Quality detection patterns
QUALITY_PATTERNS = [
    (re.compile(r'\b(\d{3,4}[pi])\b', re.IGNORECASE), lambda m: m.group(1)),  # 1080p, 720p
    (re.compile(r'\b(4k|2160p)\b', re.IGNORECASE), lambda m: "4k"),
    (re.compile(r'\b(2k|1440p)\b', re.IGNORECASE), lambda m: "2k"),
    (re.compile(r'\b(HDRip|HDTV)\b', re.IGNORECASE), lambda m: m.group(1)),
    (re.compile(r'\b(4kX264|4kx265)\b', re.IGNORECASE), lambda m: m.group(1)),
    (re.compile(r'\[(\d{3,4}[pi])\]', re.IGNORECASE), lambda m: m.group(1))  # [1080p]
]

async def autorename_exec(path, format_str, user_id=None):
    if not format_str:
        return path

    orig_filename = ospath.basename(path)
    name, ext = ospath.splitext(orig_filename)

    season = "N/A"
    episode = "N/A"
    quality = "N/A"
    audio = "N/A"

    # Extract season and episode
    for pattern, fields in SEASON_EPISODE_PATTERNS:
        match = pattern.search(name)
        if match:
            if fields == ('season', 'episode'):
                season = match.group(1).zfill(2)
                episode = match.group(2).zfill(2)
            elif fields == (None, 'episode'):
                episode = match.group(1).zfill(2)
            break

    # Extract quality
    for pattern, func in QUALITY_PATTERNS:
        match = pattern.search(name)
        if match:
            quality = func(match)
            break

    # Extract audio and quality from media info if not already found
    duration, qual, lang, stitles, title = await get_media_info(path, extra_info=True)
    if lang:
        audio = lang
    if qual and quality == "N/A":
        quality = qual

    if user_id:
        user_dict = user_data.get(user_id, {})
        title = user_dict.get('TITLE') or title

    if not title:
        title = "N/A"

    try:
        new_name = format_str.format(
            quality=quality,
            audio=audio,
            Season=season,
            episode=episode,
            filename=name,
            basename=name,
            title=title
        )
    except KeyError as e:
        LOGGER.error(f"Autorename Error: Missing key {e} in format string: {format_str}")
        return path
    except Exception as e:
        LOGGER.error(f"Autorename Error: {e}")
        return path

    new_name = MetadataProcessor().sanitize(new_name)

    # Add extension back
    if not new_name.lower().endswith(ext.lower()):
        new_name += ext

    return ospath.join(ospath.dirname(path), new_name)
