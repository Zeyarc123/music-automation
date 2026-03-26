"""
Platform and title configuration for the music automation suite.
"""

# Default platform configurations
# Each platform defines how titles and metadata should be formatted.
# You can customize these or add new platforms.

PLATFORMS = {
    'youtube': {
        'language': 'en',
        'title_template': '{bpm} BPM - {key_en} - {title} ({type_en})',
        'description_template': (
            '{title}\n'
            'BPM: {bpm}\n'
            'Key: {key_en}\n'
            'Type: {type_en}\n'
            '\n'
            '#beats #typebeat #{genre}'
        ),
        'tags_language': 'en',
    },
    'discord_fr': {
        'language': 'fr',
        'title_template': '{bpm} BPM - {key_fr} - {title} ({type_fr})',
        'description_template': (
            '{title}\n'
            'BPM : {bpm}\n'
            'Tonalité : {key_fr}\n'
            'Type : {type_fr}'
        ),
        'tags_language': 'fr',
    },
    'discord_en': {
        'language': 'en',
        'title_template': '{bpm} BPM - {key_en} - {title} ({type_en})',
        'description_template': (
            '{title}\n'
            'BPM: {bpm}\n'
            'Key: {key_en}\n'
            'Type: {type_en}'
        ),
        'tags_language': 'en',
    },
    'beatstars': {
        'language': 'en',
        'title_template': '{title} - {key_en} {bpm} BPM',
        'description_template': (
            '{title}\n'
            'Key: {key_en}\n'
            'BPM: {bpm}\n'
            'Type: {type_en}\n'
            '\n'
            '#{genre} #typebeat'
        ),
        'tags_language': 'en',
    },
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
