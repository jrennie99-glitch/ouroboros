"""Ouroboros — Music Production tools."""

from __future__ import annotations
import json, random
from typing import Any, Dict, List
from ouroboros.tools._adapter import adapt_tools

NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
SCALES = {
    "major": [0,2,4,5,7,9,11], "minor": [0,2,3,5,7,8,10],
    "dorian": [0,2,3,5,7,9,10], "mixolydian": [0,2,4,5,7,9,10],
    "pentatonic_major": [0,2,4,7,9], "pentatonic_minor": [0,3,5,7,10],
    "blues": [0,3,5,6,7,10], "harmonic_minor": [0,2,3,5,7,8,11],
}

GENRE_BEATS = {
    "trap": {"bpm": "140-160", "kick": "x---x---x---x-x-", "snare": "----x-------x---",
             "hihat": "x-x-x-x-x-x-x-x-", "bass": "x---x-------x-x-"},
    "boom_bap": {"bpm": "85-95", "kick": "x--x----x--x----", "snare": "----x-------x---",
                 "hihat": "x-x-x-x-x-x-x-x-", "bass": "x-------x-------"},
    "rnb": {"bpm": "65-80", "kick": "x-------x-----x-", "snare": "----x-------x---",
            "hihat": "x-x-x-x-x-x-x-x-", "bass": "x-----x-x-------"},
    "pop": {"bpm": "100-130", "kick": "x---x---x---x---", "snare": "----x-------x---",
            "hihat": "x-x-x-x-x-x-x-x-", "bass": "x---x---x---x---"},
    "edm": {"bpm": "126-132", "kick": "x---x---x---x---", "snare": "----x-------x---",
            "hihat": "--x---x---x---x-", "bass": "x---x---x-x-x---"},
    "lofi": {"bpm": "70-90", "kick": "x-----x-x-------", "snare": "----x-----x-x---",
             "hihat": "x-x---x-x-x---x-", "bass": "x-------x-----x-"},
}

GENRE_CHORDS = {
    "pop": [["I", "V", "vi", "IV"], ["I", "IV", "V", "V"]],
    "rnb": [["IVmaj7", "iii7", "vi7", "V7"], ["IIm9", "V13", "Imaj9", "Imaj9"]],
    "trap": [["i", "VI", "VII", "i"], ["i", "iv", "VI", "VII"]],
    "edm": [["vi", "IV", "I", "V"], ["I", "V", "vi", "iii"]],
    "jazz": [["IImaj7", "V7", "Imaj7", "Imaj7"], ["iii7", "VI7", "ii7", "V7"]],
    "lofi": [["IVmaj7", "iii7", "vi9", "Imaj7"], ["ii9", "V7", "Imaj9", "vi7"]],
    "boom_bap": [["i", "iv", "VII", "III"], ["i", "VI", "v", "VII"]],
}

GENRE_BPM = {
    "trap": (140, 160), "boom_bap": (85, 95), "rnb": (65, 80), "pop": (100, 130),
    "edm": (126, 132), "lofi": (70, 90), "drill": (140, 145), "house": (120, 130),
    "dnb": (170, 180), "reggaeton": (90, 100), "hip_hop": (80, 115),
    "rock": (110, 140), "jazz": (100, 160), "classical": (60, 140),
}


def beat_maker(genre: str = "trap", swing: int = 0, variation: str = "basic") -> Dict:
    g = genre.lower().replace("-", "_").replace(" ", "_")
    beat = GENRE_BEATS.get(g, GENRE_BEATS["trap"]).copy()
    beat["genre"] = g
    beat["swing_percent"] = swing
    beat["variation"] = variation
    if variation == "half_time":
        beat["snare"] = "--------x---------------x-------"
    elif variation == "double_time":
        beat["hihat"] = "xxxxxxxxxxxxxxxx"
    beat["grid_legend"] = "x=hit, -=rest | each char = 1/16th note"
    return beat


def chord_progression(genre: str = "pop", key: str = "C", mood: str = "uplifting",
                      bars: int = 4) -> Dict:
    g = genre.lower().replace("-", "_").replace(" ", "_")
    progs = GENRE_CHORDS.get(g, GENRE_CHORDS["pop"])
    prog = random.choice(progs)
    root_idx = NOTES.index(key) if key in NOTES else 0
    voicings = []
    for numeral in prog:
        voicings.append({"numeral": numeral, "root": key, "voicing": "root_position",
                         "suggestion": f"Try 1st inversion for smoother voice leading"})
    return {"key": key, "genre": g, "mood": mood, "bars": bars,
            "progression": prog, "voicings": voicings,
            "tip": "Use inversions to keep bass movement stepwise"}


def song_structure(genre: str = "pop", energy: str = "medium",
                   duration_minutes: float = 3.5) -> Dict:
    structures = {
        "pop": [("Intro", 4), ("Verse 1", 8), ("Pre-Chorus", 4), ("Chorus", 8),
                ("Verse 2", 8), ("Pre-Chorus", 4), ("Chorus", 8), ("Bridge", 8),
                ("Chorus", 8), ("Outro", 4)],
        "trap": [("Intro", 4), ("Hook", 8), ("Verse 1", 16), ("Hook", 8),
                 ("Verse 2", 16), ("Hook", 8), ("Bridge", 8), ("Hook", 8), ("Outro", 4)],
        "edm": [("Intro", 16), ("Buildup", 8), ("Drop", 16), ("Breakdown", 8),
                ("Buildup 2", 8), ("Drop 2", 16), ("Outro", 8)],
        "rnb": [("Intro", 4), ("Verse 1", 8), ("Chorus", 8), ("Verse 2", 8),
                ("Chorus", 8), ("Bridge", 8), ("Chorus", 8), ("Outro", 4)],
        "boom_bap": [("Intro", 4), ("Verse 1", 16), ("Hook", 8), ("Verse 2", 16),
                     ("Hook", 8), ("Verse 3", 16), ("Hook", 8), ("Outro", 4)],
    }
    g = genre.lower().replace("-", "_").replace(" ", "_")
    sections = structures.get(g, structures["pop"])
    total_bars = sum(b for _, b in sections)
    arrangement = []
    for name, bars in sections:
        arrangement.append({"section": name, "bars": bars,
                            "energy": "high" if "Chorus" in name or "Drop" in name else energy})
    return {"genre": g, "total_bars": total_bars, "sections": arrangement,
            "est_duration_min": round(total_bars * 4 * 60 / (120 * 4), 1),
            "tip": "Add 2-bar transitions between sections for smoother flow"}


def mixing_guide(instruments: List[str] = None, genre: str = "pop") -> Dict:
    instruments = instruments or ["kick", "snare", "bass", "vocals", "synth", "hihat"]
    presets = {
        "kick": {"eq": "HPF 30Hz, boost 60-80Hz +3dB, cut 300Hz -2dB",
                 "compression": "ratio 4:1, attack 10ms, release 50ms",
                 "panning": "center", "reverb": "none", "level": "-6dB"},
        "snare": {"eq": "HPF 80Hz, boost 200Hz +2dB, boost 5kHz +3dB for snap",
                  "compression": "ratio 3:1, attack 5ms, release 80ms",
                  "panning": "center", "reverb": "short plate 10-15%", "level": "-8dB"},
        "bass": {"eq": "HPF 30Hz, boost 80-100Hz +2dB, cut 250Hz -2dB",
                 "compression": "ratio 4:1, attack 20ms, release 100ms",
                 "panning": "center", "reverb": "none", "level": "-8dB"},
        "vocals": {"eq": "HPF 80Hz, cut 300Hz -3dB, boost 3kHz +2dB, boost 10kHz +1dB (air)",
                   "compression": "ratio 3:1, attack 10ms, release 60ms",
                   "panning": "center", "reverb": "medium plate 15-25%", "level": "-6dB"},
        "synth": {"eq": "HPF 100Hz, boost 1-3kHz +2dB for presence",
                  "compression": "ratio 2:1, attack 15ms, release 100ms",
                  "panning": "L30-R30", "reverb": "hall 20-30%", "level": "-10dB"},
        "hihat": {"eq": "HPF 300Hz, boost 8-12kHz +2dB",
                  "compression": "ratio 2:1, attack 1ms, release 30ms",
                  "panning": "R20-R40", "reverb": "short room 5%", "level": "-12dB"},
    }
    guide = {}
    for inst in instruments:
        key = inst.lower().replace(" ", "_")
        guide[inst] = presets.get(key, {"eq": "HPF 100Hz, shape to taste",
                                        "compression": "ratio 2:1, attack 10ms",
                                        "panning": "to taste", "reverb": "10-20%",
                                        "level": "-10dB"})
    return {"genre": genre, "instruments": guide,
            "bus_tips": {"drum_bus": "glue compressor, ratio 2:1, 1-2dB GR",
                         "master_bus": "gentle compression, 1dB GR max before mastering"},
            "gain_staging": "Keep peaks around -6dB on individual tracks"}


def mastering_chain(genre: str = "pop", loudness_target: str = "-14 LUFS") -> Dict:
    chains = {
        "pop": [
            {"step": 1, "plugin": "Linear Phase EQ", "settings": "HPF 25Hz, gentle broad boosts"},
            {"step": 2, "plugin": "Multiband Compressor", "settings": "3 bands: <200Hz 3:1, 200-2kHz 2:1, >2kHz 2:1"},
            {"step": 3, "plugin": "Stereo Width", "settings": "Widen above 300Hz, mono below"},
            {"step": 4, "plugin": "Tape Saturation", "settings": "Subtle warmth, drive 10-15%"},
            {"step": 5, "plugin": "Limiter", "settings": f"Ceiling -1dB, target {loudness_target}"},
        ],
        "trap": [
            {"step": 1, "plugin": "EQ", "settings": "Boost sub 40-60Hz, cut mud 200-400Hz"},
            {"step": 2, "plugin": "Multiband Compressor", "settings": "Heavy low end control"},
            {"step": 3, "plugin": "Soft Clipper", "settings": "Gentle clipping for loudness"},
            {"step": 4, "plugin": "Limiter", "settings": f"Ceiling -0.5dB, target {loudness_target}"},
        ],
        "edm": [
            {"step": 1, "plugin": "EQ", "settings": "HPF 20Hz, surgical cuts"},
            {"step": 2, "plugin": "Multiband Compressor", "settings": "Aggressive, 4 bands"},
            {"step": 3, "plugin": "Stereo Enhancer", "settings": "Wide mids and highs"},
            {"step": 4, "plugin": "Clipper + Limiter", "settings": f"Ceiling -0.3dB, loud, target {loudness_target}"},
        ],
    }
    g = genre.lower().replace("-", "_").replace(" ", "_")
    chain = chains.get(g, chains["pop"])
    return {"genre": g, "loudness_target": loudness_target, "chain": chain,
            "reference_tip": "A/B against 2-3 reference tracks in the same genre",
            "formats": {"streaming": "-14 LUFS", "club": "-6 to -8 LUFS", "cd": "-9 to -12 LUFS"}}


def sample_pack_creator(pack_name: str = "Custom Pack", genre: str = "trap",
                        count: int = 20) -> Dict:
    categories = {
        "drums": {"kick": 4, "snare": 4, "hihat": 4, "clap": 2, "perc": 2},
        "bass": {"808": 3, "sub": 2, "reese": 1},
        "synths": {"lead": 2, "pad": 2, "pluck": 2},
        "fx": {"riser": 2, "downlifter": 1, "impact": 1, "ambient": 1},
    }
    samples = []
    idx = 1
    for cat, types in categories.items():
        for stype, n in types.items():
            for i in range(1, n + 1):
                samples.append({"id": idx, "category": cat, "type": stype,
                                "name": f"{genre}_{stype}_{i:02d}",
                                "format": "WAV 24bit 44.1kHz",
                                "description": f"{genre.title()} {stype} sample {i}"})
                idx += 1
                if idx > count:
                    break
            if idx > count:
                break
        if idx > count:
            break
    return {"pack_name": pack_name, "genre": genre, "total_samples": len(samples),
            "samples": samples, "organization": list(categories.keys())}


def melody_generator(key: str = "C", scale: str = "minor", bars: int = 4,
                     octave: int = 4, style: str = "melodic") -> Dict:
    sc = SCALES.get(scale, SCALES["minor"])
    root_idx = NOTES.index(key) if key in NOTES else 0
    notes_in_scale = [NOTES[(root_idx + interval) % 12] for interval in sc]
    melody = []
    durations = ["1/4", "1/8", "1/8", "1/4", "1/2", "1/4", "1/8", "1/8"]
    for bar in range(bars):
        bar_notes = []
        for beat in range(4):
            note = random.choice(notes_in_scale)
            dur = random.choice(durations)
            bar_notes.append({"note": f"{note}{octave}", "duration": dur,
                              "velocity": random.randint(80, 120)})
        melody.append({"bar": bar + 1, "notes": bar_notes})
    return {"key": key, "scale": scale, "octave": octave, "bars": bars,
            "available_notes": notes_in_scale, "melody": melody,
            "tip": "Emphasize root and 5th on strong beats for stability"}


def lyrics_writer(genre: str = "pop", mood: str = "uplifting", topic: str = "love",
                  sections: List[str] = None) -> Dict:
    sections = sections or ["verse1", "chorus", "verse2", "chorus", "bridge", "chorus"]
    templates = {
        "verse1": {"lines": 4, "rhyme_scheme": "ABAB", "tip": "Set the scene, introduce the story"},
        "chorus": {"lines": 4, "rhyme_scheme": "AABB", "tip": "Catchy hook, repeat the main message"},
        "verse2": {"lines": 4, "rhyme_scheme": "ABAB", "tip": "Develop the story, add new perspective"},
        "bridge": {"lines": 4, "rhyme_scheme": "CDCD", "tip": "Contrast, shift perspective or energy"},
        "outro": {"lines": 2, "rhyme_scheme": "AA", "tip": "Resolve or leave open-ended"},
    }
    structure = []
    for sec in sections:
        base = sec.rstrip("0123456789").rstrip(" ")
        tmpl = templates.get(base, templates.get(sec, templates["verse1"]))
        structure.append({"section": sec, **tmpl})
    return {"genre": genre, "mood": mood, "topic": topic, "sections": structure,
            "syllable_tip": "Match syllable count to your melody rhythm",
            "writing_tips": ["Start with the chorus hook", "Use concrete imagery over abstractions",
                             "Internal rhymes add flow", "Vary line lengths for dynamics"]}


def bpm_key_analyzer(genre: str = "pop", current_bpm: int = 0,
                     current_key: str = "") -> Dict:
    g = genre.lower().replace("-", "_").replace(" ", "_")
    bpm_range = GENRE_BPM.get(g, (100, 130))
    result = {"genre": g, "suggested_bpm_range": f"{bpm_range[0]}-{bpm_range[1]}",
              "sweet_spot_bpm": (bpm_range[0] + bpm_range[1]) // 2}
    popular_keys = {"pop": ["C", "G", "D", "A"], "trap": ["F#", "C#", "G#", "D#"],
                    "rnb": ["Ab", "Eb", "Bb", "F"], "edm": ["A", "F", "C", "G"],
                    "lofi": ["C", "F", "Bb", "Eb"], "boom_bap": ["D", "G", "C", "A"]}
    result["popular_keys"] = popular_keys.get(g, ["C", "G", "D", "A"])
    if current_key and current_key in NOTES:
        ki = NOTES.index(current_key)
        result["harmonic_compatible"] = {
            "camelot_adjacent": [NOTES[(ki + 7) % 12], NOTES[(ki + 5) % 12]],
            "relative_minor_major": NOTES[(ki + 9) % 12] if current_key.isupper() else NOTES[(ki + 3) % 12],
            "energy_boost": NOTES[(ki + 2) % 12],
        }
    if current_bpm:
        result["half_time"] = current_bpm // 2
        result["double_time"] = current_bpm * 2
        result["compatible_bpms"] = [current_bpm, current_bpm // 2, current_bpm * 2]
    return result


def music_business(action: str = "royalty_calc", revenue: float = 0,
                   splits: Dict = None, platform: str = "all") -> Dict:
    if action == "royalty_calc":
        rates = {"spotify": 0.004, "apple_music": 0.008, "youtube_music": 0.002,
                 "tidal": 0.013, "amazon_music": 0.004, "deezer": 0.003}
        if revenue > 0:
            streams_needed = {p: int(revenue / r) for p, r in rates.items()}
            return {"target_revenue": revenue, "streams_needed": streams_needed,
                    "avg_rate_per_stream": rates, "note": "Rates vary by country and subscription type"}
        return {"avg_rate_per_stream": rates, "tip": "Focus on playlist placement for volume"}

    elif action == "split_sheet":
        splits = splits or {"artist": 50, "producer": 25, "writer": 25}
        total = sum(splits.values())
        if total != 100:
            splits = {k: round(v / total * 100, 1) for k, v in splits.items()}
        return {"splits": splits, "total_percent": 100,
                "fields_needed": ["song_title", "date", "legal_names", "pro_affiliations",
                                  "publisher_info", "ownership_percentages"],
                "tip": "Always get split sheets signed BEFORE release"}

    elif action == "distribution":
        distributors = [
            {"name": "DistroKid", "cost": "$22.99/yr", "keeps": "100% royalties", "best_for": "indie artists"},
            {"name": "TuneCore", "cost": "$9.99/single", "keeps": "100% royalties", "best_for": "established indie"},
            {"name": "CD Baby", "cost": "$9.95/single", "keeps": "91% royalties", "best_for": "physical + digital"},
            {"name": "LANDR", "cost": "$12.99/yr", "keeps": "100% royalties", "best_for": "mastering + distribution"},
            {"name": "Amuse", "cost": "Free tier", "keeps": "100% royalties", "best_for": "beginners"},
        ]
        return {"distributors": distributors, "release_checklist": [
            "Master audio files (WAV 16/24bit 44.1kHz)", "Album artwork (3000x3000 min)",
            "ISRC codes", "Metadata (title, artist, genre, year)",
            "Schedule release 4-6 weeks ahead", "Pre-save campaign",
            "Submit to playlist curators 2 weeks before release"]}

    return {"error": f"Unknown action: {action}. Use: royalty_calc, split_sheet, distribution"}


def _raw_tools() -> list:
    return [
        {"name": "beat_maker",
         "description": "Generate beat patterns (kick/snare/hihat/bass) as grid notation for trap, boom bap, R&B, pop, EDM, lo-fi.",
         "parameters": {"type": "object", "properties": {
             "genre": {"type": "string", "enum": ["trap", "boom_bap", "rnb", "pop", "edm", "lofi"]},
             "swing": {"type": "integer", "default": 0},
             "variation": {"type": "string", "enum": ["basic", "half_time", "double_time"], "default": "basic"},
         }, "required": ["genre"]}, "function": beat_maker},

        {"name": "chord_progression",
         "description": "Generate chord progressions by genre/mood with voicings and inversions.",
         "parameters": {"type": "object", "properties": {
             "genre": {"type": "string"}, "key": {"type": "string", "default": "C"},
             "mood": {"type": "string", "default": "uplifting"}, "bars": {"type": "integer", "default": 4},
         }, "required": ["genre"]}, "function": chord_progression},

        {"name": "song_structure",
         "description": "Generate full song structures with sections, bar counts, and arrangement notes.",
         "parameters": {"type": "object", "properties": {
             "genre": {"type": "string"}, "energy": {"type": "string", "default": "medium"},
             "duration_minutes": {"type": "number", "default": 3.5},
         }, "required": ["genre"]}, "function": song_structure},

        {"name": "mixing_guide",
         "description": "Generate mixing guide with EQ, compression, reverb, panning per instrument.",
         "parameters": {"type": "object", "properties": {
             "instruments": {"type": "array", "items": {"type": "string"}},
             "genre": {"type": "string", "default": "pop"},
         }}, "function": mixing_guide},

        {"name": "mastering_chain",
         "description": "Generate mastering signal chain (EQ, multiband compression, limiting, stereo width).",
         "parameters": {"type": "object", "properties": {
             "genre": {"type": "string", "default": "pop"},
             "loudness_target": {"type": "string", "default": "-14 LUFS"},
         }}, "function": mastering_chain},

        {"name": "sample_pack_creator",
         "description": "Generate organized sample pack descriptions by type (drums, bass, synths, fx).",
         "parameters": {"type": "object", "properties": {
             "pack_name": {"type": "string", "default": "Custom Pack"},
             "genre": {"type": "string", "default": "trap"},
             "count": {"type": "integer", "default": 20},
         }}, "function": sample_pack_creator},

        {"name": "melody_generator",
         "description": "Generate melodies in any key/scale as note sequences with rhythm and velocity.",
         "parameters": {"type": "object", "properties": {
             "key": {"type": "string", "default": "C"}, "scale": {"type": "string", "default": "minor"},
             "bars": {"type": "integer", "default": 4}, "octave": {"type": "integer", "default": 4},
             "style": {"type": "string", "default": "melodic"},
         }}, "function": melody_generator},

        {"name": "lyrics_writer",
         "description": "Write lyrics structure by genre/mood/topic with verse/chorus/bridge and writing tips.",
         "parameters": {"type": "object", "properties": {
             "genre": {"type": "string", "default": "pop"}, "mood": {"type": "string", "default": "uplifting"},
             "topic": {"type": "string", "default": "love"},
             "sections": {"type": "array", "items": {"type": "string"}},
         }}, "function": lyrics_writer},

        {"name": "bpm_key_analyzer",
         "description": "Suggest BPM ranges and keys for genres, calculate harmonic mixing compatibility.",
         "parameters": {"type": "object", "properties": {
             "genre": {"type": "string", "default": "pop"},
             "current_bpm": {"type": "integer", "default": 0},
             "current_key": {"type": "string", "default": ""},
         }}, "function": bpm_key_analyzer},

        {"name": "music_business",
         "description": "Music business tools: royalty calculator, split sheet generator, distribution strategy.",
         "parameters": {"type": "object", "properties": {
             "action": {"type": "string", "enum": ["royalty_calc", "split_sheet", "distribution"]},
             "revenue": {"type": "number", "default": 0},
             "splits": {"type": "object"}, "platform": {"type": "string", "default": "all"},
         }, "required": ["action"]}, "function": music_business},
    ]


def get_tools():
    return adapt_tools(_raw_tools())
