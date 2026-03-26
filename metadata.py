"""
Metadata manager — builds per-platform titles, renames files, handles batch metadata.
"""

import os
import json
import shutil
from config import PLATFORMS, TRACK_TYPES, KEY_DISPLAY


def build_key_string(analysis_result, language):
    """Build a key string like 'C# minor' or 'Do# mineur' from analysis result."""
    key_data = analysis_result['key']
    if language == 'fr':
        template = KEY_DISPLAY['fr'][key_data['mode']]
        return template.format(note_fr=key_data['key_fr'])
    else:
        template = KEY_DISPLAY['en'][key_data['mode']]
        return template.format(note=key_data['key'])


def build_title(analysis_result, platform, title, track_type='loop', genre=''):
    """
    Build a formatted title for a specific platform.

    Args:
        analysis_result: Output from analyzer.analyze_file()
        platform: Platform name (key in PLATFORMS dict) or a custom dict
        title: The base title/name for the track
        track_type: One of: loop, full, sample, oneshot, drumkit, melody, vocals
        genre: Genre tag (e.g., 'trap', 'drill', 'rnb')

    Returns:
        Formatted title string
    """
    if isinstance(platform, str):
        config = PLATFORMS[platform]
    else:
        config = platform

    lang = config['language']
    bpm = analysis_result['bpm']['bpm']
    key_en = build_key_string(analysis_result, 'en')
    key_fr = build_key_string(analysis_result, 'fr')

    type_info = TRACK_TYPES.get(track_type, TRACK_TYPES['loop'])
    type_en = type_info['en']
    type_fr = type_info['fr']

    return config['title_template'].format(
        bpm=bpm,
        key_en=key_en,
        key_fr=key_fr,
        title=title,
        type_en=type_en,
        type_fr=type_fr,
        genre=genre,
    )


def build_description(analysis_result, platform, title, track_type='loop', genre=''):
    """Build a formatted description for a specific platform."""
    if isinstance(platform, str):
        config = PLATFORMS[platform]
    else:
        config = platform

    bpm = analysis_result['bpm']['bpm']
    key_en = build_key_string(analysis_result, 'en')
    key_fr = build_key_string(analysis_result, 'fr')

    type_info = TRACK_TYPES.get(track_type, TRACK_TYPES['loop'])
    type_en = type_info['en']
    type_fr = type_info['fr']

    return config['description_template'].format(
        bpm=bpm,
        key_en=key_en,
        key_fr=key_fr,
        title=title,
        type_en=type_en,
        type_fr=type_fr,
        genre=genre,
    )


def build_filename(analysis_result, title, track_type='loop', extension=None):
    """
    Build a clean filename with BPM and key embedded.
    Example: '130BPM_Csharp-minor_dark-melody_loop.wav'
    """
    bpm = int(analysis_result['bpm']['bpm'])
    key_name = analysis_result['key']['key'].replace('#', 'sharp')
    mode = analysis_result['key']['mode']

    # Clean the title for filename use
    clean_title = title.strip().replace(' ', '-').lower()
    for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        clean_title = clean_title.replace(char, '')

    type_label = track_type

    if extension is None:
        extension = '.wav'
    if not extension.startswith('.'):
        extension = '.' + extension

    return f"{bpm}BPM_{key_name}-{mode}_{clean_title}_{type_label}{extension}"


def rename_file(file_path, analysis_result, title, track_type='loop', dry_run=False):
    """
    Rename a file with BPM and key in the filename.

    Args:
        file_path: Current path to the file
        analysis_result: Output from analyzer.analyze_file()
        title: Base title for the track
        track_type: Type of track
        dry_run: If True, return the new path without actually renaming

    Returns:
        New file path
    """
    directory = os.path.dirname(file_path)
    extension = os.path.splitext(file_path)[1]
    new_name = build_filename(analysis_result, title, track_type, extension)
    new_path = os.path.join(directory, new_name)

    if dry_run:
        return new_path

    if os.path.exists(new_path) and new_path != file_path:
        # Add a number suffix to avoid overwriting
        base, ext = os.path.splitext(new_name)
        counter = 2
        while os.path.exists(os.path.join(directory, f"{base}_{counter}{ext}")):
            counter += 1
        new_name = f"{base}_{counter}{ext}"
        new_path = os.path.join(directory, new_name)

    os.rename(file_path, new_path)
    return new_path


def build_all_titles(analysis_result, title, track_type='loop', genre='',
                     platforms=None):
    """
    Build titles for all (or specified) platforms at once.

    Returns:
        Dict of {platform_name: {'title': ..., 'description': ...}}
    """
    if platforms is None:
        platforms = list(PLATFORMS.keys())

    result = {}
    for platform in platforms:
        result[platform] = {
            'title': build_title(analysis_result, platform, title, track_type, genre),
            'description': build_description(analysis_result, platform, title,
                                             track_type, genre),
        }
    return result


def process_batch(analysis_results, titles, track_types=None, genre='',
                  platforms=None, rename=False, dry_run=False):
    """
    Process a batch of analyzed files: generate titles for all platforms and optionally rename.

    Args:
        analysis_results: List of results from analyzer.analyze_batch()
        titles: List of base titles (same length as analysis_results)
        track_types: List of track types, or a single type for all
        genre: Genre string
        platforms: List of platform names, or None for all
        rename: Whether to rename files
        dry_run: If True, show what would happen without doing it

    Returns:
        List of dicts with all metadata per file
    """
    if isinstance(track_types, str) or track_types is None:
        track_types = [track_types or 'loop'] * len(analysis_results)

    output = []
    for i, result in enumerate(analysis_results):
        if 'error' in result:
            output.append(result)
            continue

        title = titles[i] if i < len(titles) else os.path.splitext(result['file'])[0]
        track_type = track_types[i] if i < len(track_types) else 'loop'

        entry = {
            'file': result['file'],
            'path': result['path'],
            'bpm': result['bpm']['bpm'],
            'bpm_half': result['bpm']['bpm_half'],
            'bpm_confidence': result['bpm']['confidence'],
            'key': f"{result['key']['key']} {result['key']['mode']}",
            'key_fr': f"{result['key']['key_fr']} {result['key']['mode_fr']}",
            'track_type': track_type,
            'genre': genre,
            'platforms': build_all_titles(result, title, track_type, genre, platforms),
        }

        if rename:
            new_path = rename_file(result['path'], result, title, track_type, dry_run)
            entry['renamed_to'] = new_path
            if not dry_run:
                entry['path'] = new_path

        output.append(entry)

    return output


def save_batch_metadata(batch_output, output_path):
    """Save batch metadata to a JSON file for use by the scheduler/publishers."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(batch_output, f, indent=2, ensure_ascii=False)
    return output_path
