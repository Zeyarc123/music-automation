"""
Music Automation Suite — Main entry point.
Analyzes audio files, generates per-platform titles, and optionally renames files.

Usage:
    python main.py file1.wav file2.wav ...
    python main.py folder/
    python main.py --interactive
"""

import os
import sys
import json
import argparse

from analyzer import analyze_file, analyze_batch, format_result
from metadata import (
    build_all_titles, rename_file, process_batch, save_batch_metadata,
    build_filename
)
from config import PLATFORMS, TRACK_TYPES


def find_audio_files(path):
    """Find all audio files in a directory."""
    extensions = {'.wav', '.mp3', '.flac', '.ogg', '.aiff', '.aif'}
    files = []
    if os.path.isfile(path):
        files.append(path)
    elif os.path.isdir(path):
        for entry in sorted(os.listdir(path)):
            if os.path.splitext(entry)[1].lower() in extensions:
                files.append(os.path.join(path, entry))
    return files


def interactive_mode(files):
    """Interactive mode: ask user for metadata per file."""
    print("\n=== Interactive Mode ===")
    print(f"Found {len(files)} file(s)\n")

    # Global settings
    print("--- Global Settings ---")
    print(f"Available track types: {', '.join(TRACK_TYPES.keys())}")
    default_type = input("Default track type [loop]: ").strip() or 'loop'
    genre = input("Genre (e.g., trap, drill, rnb) []: ").strip()

    print(f"\nAvailable platforms: {', '.join(PLATFORMS.keys())}")
    platform_input = input("Platforms (comma-separated, or 'all') [all]: ").strip()
    if platform_input and platform_input != 'all':
        platforms = [p.strip() for p in platform_input.split(',')]
    else:
        platforms = None  # all

    do_rename = input("Rename files with BPM/key? (y/n) [n]: ").strip().lower() == 'y'

    # Analyze all files first
    print("\n--- Analyzing ---")
    results = []
    for i, f in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}]")
        try:
            result = analyze_file(f)
            results.append(result)
            print(format_result(result))
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({'file': os.path.basename(f), 'error': str(e)})

    # Collect titles per file
    print("\n--- Title Configuration ---")
    titles = []
    track_types = []
    for i, result in enumerate(results):
        if 'error' in result:
            titles.append('')
            track_types.append(default_type)
            continue

        print(f"\nFile: {result['file']}")
        print(f"  BPM: {result['bpm']['bpm']}  Key: {result['key']['key']} {result['key']['mode']}")

        # Suggest a clean title from filename
        suggested = os.path.splitext(result['file'])[0]
        title = input(f"  Title [{suggested}]: ").strip() or suggested
        titles.append(title)

        tt = input(f"  Track type [{default_type}]: ").strip() or default_type
        track_types.append(tt)

    # Process batch
    print("\n--- Generating Metadata ---")
    batch = process_batch(
        results, titles, track_types, genre, platforms,
        rename=do_rename, dry_run=False,
    )

    # Display results
    for entry in batch:
        if 'error' in entry:
            print(f"\n  SKIPPED: {entry['file']} ({entry['error']})")
            continue

        print(f"\n  {entry['file']}")
        print(f"  BPM: {entry['bpm']}  Key: {entry['key']}")
        if 'renamed_to' in entry:
            print(f"  Renamed to: {os.path.basename(entry['renamed_to'])}")

        for platform, data in entry['platforms'].items():
            print(f"  [{platform}] {data['title']}")

    # Save metadata
    output_path = input("\nSave metadata JSON to [batch_metadata.json]: ").strip()
    output_path = output_path or 'batch_metadata.json'
    save_batch_metadata(batch, output_path)
    print(f"Saved to {output_path}")

    return batch


def cli_mode(args):
    """Non-interactive CLI mode."""
    files = []
    for path in args.files:
        files.extend(find_audio_files(path))

    if not files:
        print("No audio files found.")
        sys.exit(1)

    print(f"Found {len(files)} file(s)")
    print(f"BPM range: {args.min_bpm}-{args.max_bpm}")
    print("=" * 50)

    # Analyze
    results = analyze_batch(files, args.min_bpm, args.max_bpm)

    # Build titles (use filename as default title)
    titles = [os.path.splitext(r.get('file', '')) [0] for r in results]

    # Process
    platforms = args.platforms.split(',') if args.platforms else None
    batch = process_batch(
        results, titles, args.type, args.genre, platforms,
        rename=args.rename, dry_run=args.dry_run,
    )

    # Output
    if args.output:
        save_batch_metadata(batch, args.output)
        print(f"\nMetadata saved to {args.output}")

    if args.json:
        print(json.dumps(batch, indent=2, ensure_ascii=False))
    else:
        for entry in batch:
            if 'error' in entry:
                print(f"\n  SKIPPED: {entry.get('file', '?')} ({entry['error']})")
                continue
            print(f"\n  {entry['file']}")
            print(f"  BPM: {entry['bpm']}  Key: {entry['key']}")
            if 'renamed_to' in entry:
                print(f"  → {os.path.basename(entry['renamed_to'])}")
            for platform, data in entry['platforms'].items():
                print(f"  [{platform}] {data['title']}")

    return batch


def main():
    parser = argparse.ArgumentParser(
        description='Music Automation Suite — Analyze, tag, and prepare music for publishing'
    )
    parser.add_argument('files', nargs='*', help='Audio files or folders to process')
    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Interactive mode (prompts for each file)')
    parser.add_argument('--type', '-t', default='loop',
                        help=f'Track type: {", ".join(TRACK_TYPES.keys())} (default: loop)')
    parser.add_argument('--genre', '-g', default='', help='Genre tag')
    parser.add_argument('--platforms', '-p', default=None,
                        help='Comma-separated platform names (default: all)')
    parser.add_argument('--rename', action='store_true',
                        help='Rename files with BPM/key in filename')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would happen without making changes')
    parser.add_argument('--min-bpm', type=int, default=70, help='Min expected BPM')
    parser.add_argument('--max-bpm', type=int, default=180, help='Max expected BPM')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--output', '-o', default=None,
                        help='Save metadata to JSON file')
    parser.add_argument('--lang', default='en', help='Default display language')

    args = parser.parse_args()

    if args.interactive:
        interactive_mode(args.files if args.files else [])
    elif args.files:
        cli_mode(args)
    else:
        # No arguments = double-clicked or launched without args → open GUI
        from gui import main as gui_main
        gui_main()


if __name__ == '__main__':
    main()
