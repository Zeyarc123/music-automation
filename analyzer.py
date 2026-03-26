"""
Music Analyzer — Detects BPM and musical key from WAV files.
Uses multiple detection methods and cross-checks for accuracy.
"""

import numpy as np
import librosa
import os
import sys
import json
from genre_detector import detect_genre


# Krumhansl-Kessler key profiles (standard in music information retrieval)
MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# French equivalents
NOTE_NAMES_FR = ['Do', 'Do#', 'Ré', 'Ré#', 'Mi', 'Fa', 'Fa#', 'Sol', 'Sol#', 'La', 'La#', 'Si']


def _correlate_key(chroma_mean):
    """Find best key match for a chroma vector using Krumhansl-Kessler profiles."""
    correlations = []
    for shift in range(12):
        major_shifted = np.roll(MAJOR_PROFILE, shift)
        minor_shifted = np.roll(MINOR_PROFILE, shift)
        correlations.append(('major', shift, np.corrcoef(chroma_mean, major_shifted)[0, 1]))
        correlations.append(('minor', shift, np.corrcoef(chroma_mean, minor_shifted)[0, 1]))
    correlations.sort(key=lambda x: x[2], reverse=True)
    return correlations


def detect_key(y, sr):
    """Detect musical key using 2 chroma methods and cross-checking."""
    # Method 1: CQT chroma (better for harmonic content)
    chroma_cqt = librosa.feature.chroma_cqt(y=y, sr=sr)
    corr_cqt = _correlate_key(np.mean(chroma_cqt, axis=1))

    # Method 2: STFT chroma (better for percussive content)
    chroma_stft = librosa.feature.chroma_stft(y=y, sr=sr)
    corr_stft = _correlate_key(np.mean(chroma_stft, axis=1))

    # Method 3: CQT chroma with harmonic component only (filters out percussion)
    y_harmonic = librosa.effects.harmonic(y)
    chroma_harm = librosa.feature.chroma_cqt(y=y_harmonic, sr=sr)
    corr_harm = _correlate_key(np.mean(chroma_harm, axis=1))

    # Cross-check: each method votes for its top pick
    votes = {}
    methods = {'cqt': corr_cqt, 'stft': corr_stft, 'harmonic': corr_harm}
    method_results = {}

    for name, corr in methods.items():
        top = corr[0]
        key_id = f"{NOTE_NAMES[top[1]]} {top[0]}"
        method_results[name] = key_id
        votes[key_id] = votes.get(key_id, 0) + 1

    # Pick the key with the most votes; tie-break by harmonic method (most reliable)
    best_votes = max(votes.values())
    candidates = [k for k, v in votes.items() if v == best_votes]

    if len(candidates) == 1:
        winner = candidates[0]
    else:
        # Tie: prefer the harmonic method's result
        winner = method_results['harmonic']

    # Parse winner
    parts = winner.split()
    best_key_name = parts[0]
    best_mode = parts[1]
    best_key = NOTE_NAMES.index(best_key_name)

    # Confidence based on agreement
    if best_votes == 3:
        confidence = 'high'
    elif best_votes == 2:
        confidence = 'medium'
    else:
        confidence = 'low'

    # Compute the relative key (major <-> minor)
    if best_mode == 'major':
        relative_idx = (best_key - 3) % 12
        relative_mode = 'minor'
        relative_mode_fr = 'mineur'
    else:
        relative_idx = (best_key + 3) % 12
        relative_mode = 'major'
        relative_mode_fr = 'majeur'

    # Runner-up from the harmonic method
    runner_up = corr_harm[1]

    return {
        'key': NOTE_NAMES[best_key],
        'key_fr': NOTE_NAMES_FR[best_key],
        'mode': best_mode,
        'mode_fr': 'majeur' if best_mode == 'major' else 'mineur',
        'relative_key': NOTE_NAMES[relative_idx],
        'relative_key_fr': NOTE_NAMES_FR[relative_idx],
        'relative_mode': relative_mode,
        'relative_mode_fr': relative_mode_fr,
        'confidence': confidence,
        'method_votes': method_results,
        'runner_up': f"{NOTE_NAMES[runner_up[1]]} {runner_up[0]}",
    }


def detect_bpm_beat_track(y, sr):
    """Method 1: librosa.beat.beat_track (dynamic programming)."""
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    tempo = np.atleast_1d(tempo)[0]
    return float(np.round(tempo))


def detect_bpm_onset(y, sr):
    """Method 2: Onset-based autocorrelation."""
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo = librosa.feature.tempo(onset_envelope=onset_env, sr=sr)
    return float(np.round(tempo[0]))


def detect_bpm_tempogram(y, sr):
    """Method 3: Tempogram-based detection."""
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempogram = librosa.feature.tempogram(onset_envelope=onset_env, sr=sr)
    # Get the dominant tempo from the tempogram
    tempo_frequencies = np.abs(np.fft.rfft(np.mean(tempogram, axis=1)))
    # Use librosa's built-in tempo estimation with tempogram
    tempo = librosa.feature.tempo(onset_envelope=onset_env, sr=sr, aggregate=None)
    return float(np.round(np.median(tempo)))


def normalize_bpm(bpm, min_bpm=70, max_bpm=180):
    """Normalize BPM to expected range by doubling/halving."""
    while bpm < min_bpm:
        bpm *= 2
    while bpm > max_bpm:
        bpm /= 2
    return round(bpm)


def cross_check_bpm(bpm_results, min_bpm=70, max_bpm=180):
    """Cross-check multiple BPM results and resolve octave errors."""
    # Normalize all results to the same range
    normalized = [normalize_bpm(b, min_bpm, max_bpm) for b in bpm_results]

    # Check if results agree (within 5 BPM tolerance)
    spread = max(normalized) - min(normalized)

    if spread <= 5:
        final_bpm = round(np.median(normalized))
        confidence = 'high'
    elif spread <= 15:
        final_bpm = round(np.median(normalized))
        confidence = 'medium'
    else:
        final_bpm = round(np.median(normalized))
        confidence = 'low'

    # Also provide the half-time BPM as an alternative
    half_bpm = round(final_bpm / 2)

    return {
        'bpm': final_bpm,
        'bpm_half': half_bpm,
        'confidence': confidence,
        'raw_values': bpm_results,
        'normalized_values': normalized,
    }


def analyze_file(file_path, min_bpm=70, max_bpm=180):
    """Analyze a single audio file for BPM and key."""
    print(f"Loading: {os.path.basename(file_path)}...")
    y, sr = librosa.load(file_path, sr=None)

    # Get duration
    duration = librosa.get_duration(y=y, sr=sr)

    # Detect BPM with 3 methods
    print("  Detecting BPM...")
    bpm1 = detect_bpm_beat_track(y, sr)
    bpm2 = detect_bpm_onset(y, sr)
    bpm3 = detect_bpm_tempogram(y, sr)

    bpm_result = cross_check_bpm([bpm1, bpm2, bpm3], min_bpm, max_bpm)

    # Detect key
    print("  Detecting key...")
    key_result = detect_key(y, sr)

    # Detect genre
    print("  Detecting genre...")
    genre_result = detect_genre(y, sr, bpm=bpm_result['bpm'])

    return {
        'file': os.path.basename(file_path),
        'path': file_path,
        'duration_seconds': round(duration, 1),
        'bpm': bpm_result,
        'key': key_result,
        'genre': genre_result,
    }


def format_result(result, language='en'):
    """Format the analysis result as a readable string."""
    bpm = result['bpm']['bpm']
    bpm_half = result['bpm']['bpm_half']
    bpm_conf = result['bpm']['confidence']

    if language == 'fr':
        key_name = result['key']['key_fr']
        mode = result['key']['mode_fr']
        rel_key = result['key']['relative_key_fr']
        rel_mode = result['key']['relative_mode_fr']
        key_conf = result['key']['confidence']
        lines = [
            f"  Fichier:    {result['file']}",
            f"  Durée:      {result['duration_seconds']}s",
            f"  BPM:        {bpm}  (ou half-time: {bpm_half})  (confiance: {bpm_conf})",
            f"  Tonalité:   {key_name} {mode}  (ou relatif: {rel_key} {rel_mode})  (confiance: {key_conf})",
        ]
        if bpm_conf != 'high':
            raw = result['bpm']['raw_values']
            lines.append(f"  /!\\ Valeurs brutes BPM: {raw} — vérifiez manuellement")
        if key_conf == 'low':
            lines.append(f"  /!\\ Tonalité incertaine, 2e choix: {result['key']['runner_up']}")
    else:
        key_name = result['key']['key']
        mode = result['key']['mode']
        rel_key = result['key']['relative_key']
        rel_mode = result['key']['relative_mode']
        key_conf = result['key']['confidence']
        lines = [
            f"  File:       {result['file']}",
            f"  Duration:   {result['duration_seconds']}s",
            f"  BPM:        {bpm}  (or half-time: {bpm_half})  (confidence: {bpm_conf})",
            f"  Key:        {key_name} {mode}  (or relative: {rel_key} {rel_mode})  (confidence: {key_conf})",
        ]
        if bpm_conf != 'high':
            raw = result['bpm']['raw_values']
            lines.append(f"  /!\\ Raw BPM values: {raw} — please verify manually")
        if key_conf == 'low':
            lines.append(f"  /!\\ Key uncertain, runner-up: {result['key']['runner_up']}")

    return '\n'.join(lines)


def analyze_batch(file_paths, min_bpm=70, max_bpm=180):
    """Analyze multiple files."""
    results = []
    for i, path in enumerate(file_paths, 1):
        print(f"\n[{i}/{len(file_paths)}]")
        try:
            result = analyze_file(path, min_bpm, max_bpm)
            results.append(result)
            print(format_result(result))
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({'file': os.path.basename(path), 'error': str(e)})
    return results


if __name__ == '__main__':
    # Command-line usage: python analyzer.py file1.wav file2.wav ...
    if len(sys.argv) < 2:
        print("Usage: python analyzer.py <file1.wav> [file2.wav] ...")
        print("Options:")
        print("  --min-bpm N   Minimum expected BPM (default: 70)")
        print("  --max-bpm N   Maximum expected BPM (default: 180)")
        print("  --lang fr     Output in French")
        print("  --json        Output results as JSON")
        sys.exit(1)

    # Parse arguments
    files = []
    min_bpm = 70
    max_bpm = 180
    language = 'en'
    output_json = False

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--min-bpm':
            min_bpm = int(args[i + 1])
            i += 2
        elif args[i] == '--max-bpm':
            max_bpm = int(args[i + 1])
            i += 2
        elif args[i] == '--lang':
            language = args[i + 1]
            i += 2
        elif args[i] == '--json':
            output_json = True
            i += 1
        else:
            files.append(args[i])
            i += 1

    if not files:
        print("No files provided.")
        sys.exit(1)

    # Verify files exist
    for f in files:
        if not os.path.exists(f):
            print(f"File not found: {f}")
            sys.exit(1)

    print(f"Analyzing {len(files)} file(s)...\n")
    print(f"BPM range: {min_bpm}-{max_bpm}")
    print("=" * 50)

    results = analyze_batch(files, min_bpm, max_bpm)

    if output_json:
        print("\n" + json.dumps(results, indent=2))
    else:
        print("\n" + "=" * 50)
        print(f"Done! Analyzed {len(results)} file(s).")
