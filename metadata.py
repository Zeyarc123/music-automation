"""
Metadata manager — builds per-platform titles, renames files, handles batch metadata.
"""

import os
import json
from config import TITLE_TEMPLATES, DESCRIPTION_TEMPLATES, TRACK_TYPES, KEY_DISPLAY


def build_key_string(analysis_result, language):
    """Build a key string like 'C# minor' or 'Do# mineur' from analysis result."""
    key_data = analysis_result['key']
    if language == 'fr':
        template = KEY_DISPLAY['fr'][key_data['mode']]
        return template.format(note_fr=key_data['key_fr'])
    else:
        template = KEY_DISPLAY['en'][key_data['mode']]
        return template.format(note=key_data['key'])


def _format_vars(analysis_result, title, track_type='loop', genre=''):
    """Build the common template variables dict."""
    bpm = int(analysis_result['bpm']['bpm'])
    key_en = build_key_string(analysis_result, 'en')
    key_fr = build_key_string(analysis_result, 'fr')
    type_info = TRACK_TYPES.get(track_type, TRACK_TYPES['loop'])
    genre_tag = genre.replace(' ', '').replace('-', '') if genre else 'beats'
    return {
        'bpm': bpm,
        'key_en': key_en,
        'key_fr': key_fr,
        'title': title,
        'type_en': type_info['en'],
        'type_fr': type_info['fr'],
        'genre': genre or 'N/A',
        'genre_tag': genre_tag,
    }


def build_title(analysis_result, title, language='en', track_type='loop', genre=''):
    """Build a formatted title in the given language."""
    variables = _format_vars(analysis_result, title, track_type, genre)
    template = TITLE_TEMPLATES.get(language, TITLE_TEMPLATES['en'])
    return template.format(**variables)


def build_description(analysis_result, title, language='en', track_type='loop', genre=''):
    """Build a formatted description in the given language."""
    variables = _format_vars(analysis_result, title, track_type, genre)
    template = DESCRIPTION_TEMPLATES.get(language, DESCRIPTION_TEMPLATES['en'])
    return template.format(**variables)


def build_filename(analysis_result, title, track_type='loop', extension=None):
    """Build a clean filename with BPM and key embedded."""
    bpm = int(analysis_result['bpm']['bpm'])
    key_name = analysis_result['key']['key'].replace('#', 'sharp')
    mode = analysis_result['key']['mode']

    clean_title = title.strip().replace(' ', '-').lower()
    for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        clean_title = clean_title.replace(char, '')

    if extension is None:
        extension = '.wav'
    if not extension.startswith('.'):
        extension = '.' + extension

    return f"{bpm}BPM_{key_name}-{mode}_{clean_title}_{track_type}{extension}"


def rename_file(file_path, analysis_result, title, track_type='loop', dry_run=False):
    """Rename a file with BPM and key in the filename."""
    directory = os.path.dirname(file_path)
    extension = os.path.splitext(file_path)[1]
    new_name = build_filename(analysis_result, title, track_type, extension)
    new_path = os.path.join(directory, new_name)

    if dry_run:
        return new_path

    if os.path.exists(new_path) and new_path != file_path:
        base, ext = os.path.splitext(new_name)
        counter = 2
        while os.path.exists(os.path.join(directory, f"{base}_{counter}{ext}")):
            counter += 1
        new_name = f"{base}_{counter}{ext}"
        new_path = os.path.join(directory, new_name)

    os.rename(file_path, new_path)
    return new_path


def build_platform_titles(analysis_result, title, settings, track_type='loop', genre=''):
    """
    Build titles for all enabled platforms based on user settings.
    Returns dict: {platform_name: {'title': ..., 'description': ..., 'language': ...}}
    """
    output = {}

    # Fixed platforms (YouTube, BeatStars, etc.)
    for name, config in settings.get('platforms', {}).items():
        if not config.get('enabled', True):
            continue
        lang = config.get('language', 'en')
        output[name] = {
            'title': build_title(analysis_result, title, lang, track_type, genre),
            'description': build_description(analysis_result, title, lang, track_type, genre),
            'language': lang,
        }

    # Discord servers
    for server in settings.get('discord_servers', []):
        if not server.get('enabled', True):
            continue
        lang = server.get('language', 'en')
        name = f"Discord: {server['name']}"
        output[name] = {
            'title': build_title(analysis_result, title, lang, track_type, genre),
            'description': build_description(analysis_result, title, lang, track_type, genre),
            'language': lang,
        }

    return output


def save_batch_metadata(batch_output, output_path):
    """Save batch metadata to a JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(batch_output, f, indent=2, ensure_ascii=False)
    return output_path
