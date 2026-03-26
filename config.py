"""
Platform and title configuration for the music automation suite.
"""

import os
import json

# ── Title templates ──
# Only 2 needed: English and French. Platforms just pick which language to use.
TITLE_TEMPLATES = {
    'en': '{bpm} BPM - {key_en} - {title} ({type_en})',
    'fr': '{bpm} BPM - {key_fr} - {title} ({type_fr})',
}

DESCRIPTION_TEMPLATES = {
    'en': (
        '{title}\n'
        'BPM: {bpm}\n'
        'Key: {key_en}\n'
        'Type: {type_en}\n'
        'Genre: {genre}\n'
        '\n'
        '#beats #typebeat #{genre_tag}'
    ),
    'fr': (
        '{title}\n'
        'BPM : {bpm}\n'
        'Tonalité : {key_fr}\n'
        'Type : {type_fr}\n'
        'Genre : {genre}\n'
        '\n'
        '#beats #typebeat #{genre_tag}'
    ),
}

# Track types
TRACK_TYPES = {
    'loop': {'en': 'Loop', 'fr': 'Boucle'},
    'full': {'en': 'Full Beat', 'fr': 'Beat complet'},
    'sample': {'en': 'Sample', 'fr': 'Échantillon'},
    'oneshot': {'en': 'One-Shot', 'fr': 'One-Shot'},
    'drumkit': {'en': 'Drum Kit', 'fr': 'Kit de batterie'},
    'melody': {'en': 'Melody Loop', 'fr': 'Boucle mélodique'},
    'vocals': {'en': 'Vocal Loop', 'fr': 'Boucle vocale'},
}

# Key display formats
KEY_DISPLAY = {
    'en': {
        'major': '{note} major',
        'minor': '{note} minor',
    },
    'fr': {
        'major': '{note_fr} majeur',
        'minor': '{note_fr} mineur',
    },
}

# ── User settings (persistent) ──

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user_settings.json')

DEFAULT_SETTINGS = {
    'platforms': {
        'YouTube': {'language': 'en', 'enabled': True},
        'BeatStars': {'language': 'en', 'enabled': True},
    },
    'discord_servers': [
        # {'name': 'My Server FR', 'language': 'fr', 'enabled': True},
        # {'name': 'Beatmakers EN', 'language': 'en', 'enabled': True},
    ],
    'default_track_type': 'loop',
    'default_genre': '',
    'rename_files': False,
}


def load_settings():
    """Load user settings from disk, or return defaults."""
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        # Merge with defaults so new keys are always present
        merged = {**DEFAULT_SETTINGS, **saved}
        return merged
    return dict(DEFAULT_SETTINGS)


def save_settings(settings):
    """Save user settings to disk."""
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
