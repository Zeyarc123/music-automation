"""
Genre/subgenre detector — rule-based classifier using audio features.
Focused on rap/hip-hop subgenres but also detects other broad genres.
"""

import numpy as np
import librosa


def extract_features(y, sr):
    """Extract audio features relevant for genre classification."""
    # Spectral features
    spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
    spectral_bandwidth = np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr))
    spectral_rolloff = np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr))
    spectral_flatness = np.mean(librosa.feature.spectral_flatness(y=y))

    # MFCCs (timbre)
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mfcc_means = np.mean(mfccs, axis=1)

    # Rhythm features
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo = librosa.feature.tempo(onset_envelope=onset_env, sr=sr)[0]
    onset_rate = len(librosa.onset.onset_detect(y=y, sr=sr)) / librosa.get_duration(y=y, sr=sr)

    # Percussive vs harmonic energy ratio
    y_harmonic, y_percussive = librosa.effects.hpss(y)
    harmonic_energy = np.mean(y_harmonic ** 2)
    percussive_energy = np.mean(y_percussive ** 2)
    total_energy = harmonic_energy + percussive_energy
    if total_energy > 0:
        percussive_ratio = percussive_energy / total_energy
        harmonic_ratio = harmonic_energy / total_energy
    else:
        percussive_ratio = 0.5
        harmonic_ratio = 0.5

    # Bass energy (sub 250 Hz)
    S = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)
    bass_mask = freqs < 250
    mid_mask = (freqs >= 250) & (freqs < 2000)
    high_mask = freqs >= 2000

    total_spectral_energy = np.mean(S)
    if total_spectral_energy > 0:
        bass_energy = np.mean(S[bass_mask]) / total_spectral_energy if np.any(bass_mask) else 0
        mid_energy = np.mean(S[mid_mask]) / total_spectral_energy if np.any(mid_mask) else 0
        high_energy = np.mean(S[high_mask]) / total_spectral_energy if np.any(high_mask) else 0
    else:
        bass_energy = mid_energy = high_energy = 0.33

    # Hi-hat detection: energy in 7k-15k Hz range with fast onsets
    hihat_mask = (freqs >= 7000) & (freqs <= 15000)
    hihat_energy = np.mean(S[hihat_mask]) / total_spectral_energy if (
        np.any(hihat_mask) and total_spectral_energy > 0) else 0

    # RMS energy (loudness)
    rms = np.mean(librosa.feature.rms(y=y))

    # Zero crossing rate (noisiness/percussiveness)
    zcr = np.mean(librosa.feature.zero_crossing_rate(y))

    # Tempo stability (how consistent the beat is)
    tempogram = librosa.feature.tempogram(onset_envelope=onset_env, sr=sr)
    tempo_stability = np.max(np.mean(tempogram, axis=1)) / (np.mean(tempogram) + 1e-6)

    return {
        'spectral_centroid': float(spectral_centroid),
        'spectral_bandwidth': float(spectral_bandwidth),
        'spectral_rolloff': float(spectral_rolloff),
        'spectral_flatness': float(spectral_flatness),
        'mfcc_means': mfcc_means.tolist(),
        'tempo': float(tempo),
        'onset_rate': float(onset_rate),
        'percussive_ratio': float(percussive_ratio),
        'harmonic_ratio': float(harmonic_ratio),
        'bass_energy': float(bass_energy),
        'mid_energy': float(mid_energy),
        'high_energy': float(high_energy),
        'hihat_energy': float(hihat_energy),
        'rms': float(rms),
        'zcr': float(zcr),
        'tempo_stability': float(tempo_stability),
    }


def classify_genre(features, bpm=None):
    """
    Rule-based genre classifier. Returns genre + subgenre with confidence scores.
    Focused on rap/hip-hop but detects other genres too.
    """
    tempo = bpm if bpm else features['tempo']
    bass = features['bass_energy']
    highs = features['high_energy']
    hihat = features['hihat_energy']
    perc_ratio = features['percussive_ratio']
    harm_ratio = features['harmonic_ratio']
    centroid = features['spectral_centroid']
    flatness = features['spectral_flatness']
    rms = features['rms']
    zcr = features['zcr']
    onset_rate = features['onset_rate']
    rolloff = features['spectral_rolloff']

    # Score each genre/subgenre
    scores = {}

    # ── RAP / HIP-HOP SUBGENRES ──

    # TRAP: heavy 808s, fast hi-hats, dark, 130-170 BPM
    trap_score = 0
    if 125 <= tempo <= 175:
        trap_score += 25
    if bass > 1.2:
        trap_score += 25
    if hihat > 0.3:
        trap_score += 20
    if perc_ratio > 0.3:
        trap_score += 15
    if onset_rate > 3:
        trap_score += 15
    scores['trap'] = trap_score

    # DRILL: sliding 808s, bouncy, 140-145 BPM typically (but up to 150)
    drill_score = 0
    if 135 <= tempo <= 155:
        drill_score += 30
    if bass > 1.3:
        drill_score += 25
    if perc_ratio > 0.35:
        drill_score += 20
    if hihat > 0.25:
        drill_score += 15
    if onset_rate > 3.5:
        drill_score += 10
    scores['drill'] = drill_score

    # BOOM BAP: sample-based, punchy drums, 85-100 BPM
    boombap_score = 0
    if 80 <= tempo <= 105:
        boombap_score += 30
    if perc_ratio > 0.3:
        boombap_score += 20
    if harm_ratio > 0.4:
        boombap_score += 20
    if bass > 0.8 and bass < 1.5:
        boombap_score += 15
    if onset_rate < 4:
        boombap_score += 15
    scores['boom bap'] = boombap_score

    # LO-FI HIP-HOP: muffled, low energy, 70-90 BPM
    lofi_score = 0
    if 65 <= tempo <= 95:
        lofi_score += 25
    if centroid < 2000:
        lofi_score += 25
    if rolloff < 4000:
        lofi_score += 20
    if rms < 0.1:
        lofi_score += 15
    if harm_ratio > 0.5:
        lofi_score += 15
    scores['lo-fi hip-hop'] = lofi_score

    # CLOUD RAP: ethereal, reverb-heavy, sparse, 130-160 BPM
    cloud_score = 0
    if 125 <= tempo <= 165:
        cloud_score += 20
    if harm_ratio > 0.5:
        cloud_score += 25
    if perc_ratio < 0.35:
        cloud_score += 20
    if onset_rate < 3:
        cloud_score += 20
    if flatness < 0.1:
        cloud_score += 15
    scores['cloud rap'] = cloud_score

    # PHONK: heavy bass, distorted, memphis-inspired, 130-160 BPM
    phonk_score = 0
    if 125 <= tempo <= 165:
        phonk_score += 20
    if bass > 1.4:
        phonk_score += 25
    if rms > 0.12:
        phonk_score += 20
    if zcr > 0.08:
        phonk_score += 20
    if perc_ratio > 0.35:
        phonk_score += 15
    scores['phonk'] = phonk_score

    # PLUGG / PLUGGNB: melodic, 150-170, lighter than trap
    plugg_score = 0
    if 145 <= tempo <= 175:
        plugg_score += 25
    if harm_ratio > 0.45:
        plugg_score += 25
    if bass > 0.8 and bass < 1.4:
        plugg_score += 20
    if centroid > 1500:
        plugg_score += 15
    if onset_rate < 4:
        plugg_score += 15
    scores['plugg'] = plugg_score

    # ── NON-RAP GENRES (broader detection) ──

    # R&B / SOUL: harmonic, smooth, 60-100 BPM
    rnb_score = 0
    if 55 <= tempo <= 105:
        rnb_score += 25
    if harm_ratio > 0.55:
        rnb_score += 30
    if perc_ratio < 0.3:
        rnb_score += 20
    if centroid < 2500:
        rnb_score += 15
    if flatness < 0.08:
        rnb_score += 10
    scores['r&b'] = rnb_score

    # POP: bright, mid-heavy, 100-130 BPM
    pop_score = 0
    if 95 <= tempo <= 135:
        pop_score += 25
    if centroid > 2000:
        pop_score += 20
    if harm_ratio > 0.4:
        pop_score += 20
    if rms > 0.08:
        pop_score += 15
    if flatness < 0.15:
        pop_score += 10
    scores['pop'] = pop_score

    # EDM / ELECTRONIC: high energy, steady beat, 120-150 BPM
    edm_score = 0
    if 115 <= tempo <= 155:
        edm_score += 20
    if onset_rate > 4:
        edm_score += 20
    if rms > 0.1:
        edm_score += 20
    if perc_ratio > 0.4:
        edm_score += 20
    if highs > 0.5:
        edm_score += 20
    scores['electronic'] = edm_score

    # Rank all
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # Determine if it's rap or not
    rap_subgenres = {'trap', 'drill', 'boom bap', 'lo-fi hip-hop', 'cloud rap',
                     'phonk', 'plugg'}
    top_genre = ranked[0][0]
    top_score = ranked[0][1]
    runner_up = ranked[1] if len(ranked) > 1 else (None, 0)

    is_rap = top_genre in rap_subgenres

    # Confidence
    if top_score >= 70:
        confidence = 'high'
    elif top_score >= 50:
        confidence = 'medium'
    else:
        confidence = 'low'

    return {
        'genre': 'rap' if is_rap else top_genre,
        'subgenre': top_genre if is_rap else None,
        'confidence': confidence,
        'score': top_score,
        'runner_up': runner_up[0],
        'runner_up_score': runner_up[1],
        'all_scores': dict(ranked),
        'is_rap': is_rap,
    }


def detect_genre(y, sr, bpm=None):
    """Full genre detection pipeline: extract features then classify."""
    features = extract_features(y, sr)
    result = classify_genre(features, bpm)
    result['features'] = features
    return result
