"""
Ouroboros — Media generation tools.

Music generator (chord progressions, lyrics, MIDI), video script writer,
podcast script, image prompt generator, subtitle generator.
"""

from __future__ import annotations

import json
import logging
import os
import random
import struct
import textwrap
from datetime import datetime
from typing import Any, Dict, List, Optional

from ouroboros.tools._adapter import adapt_tools

log = logging.getLogger(__name__)

WORKSPACE = os.environ.get("OUROBOROS_WORKSPACE", "/tmp/ouroboros_media")


def _ensure_workspace():
    os.makedirs(WORKSPACE, exist_ok=True)


# ── Chord Progressions & Music Theory ─────────────────────────────────────

CHORD_PROGRESSIONS = {
    "pop": {
        "major": [
            ["I", "V", "vi", "IV"],     # most common pop
            ["I", "IV", "V", "V"],
            ["vi", "IV", "I", "V"],      # Axis of Awesome
            ["I", "vi", "IV", "V"],
        ],
        "minor": [
            ["i", "VI", "III", "VII"],
            ["i", "iv", "v", "i"],
            ["i", "VII", "VI", "VII"],
        ],
    },
    "jazz": {
        "major": [
            ["IΔ7", "vi7", "ii7", "V7"],
            ["IΔ7", "IV7", "iii7", "vi7", "ii7", "V7"],
            ["IΔ7", "bVII7", "IΔ7", "IV7"],
        ],
        "minor": [
            ["i7", "iv7", "bVII7", "III7"],
            ["ii7b5", "V7b9", "i7", "i7"],
        ],
    },
    "blues": {
        "major": [
            ["I7", "I7", "I7", "I7", "IV7", "IV7", "I7", "I7", "V7", "IV7", "I7", "V7"],
        ],
    },
    "rock": {
        "major": [
            ["I", "IV", "V", "I"],
            ["I", "bVII", "IV", "I"],
            ["I", "V", "bVII", "IV"],
        ],
    },
    "lofi": {
        "major": [
            ["IΔ9", "vi9", "ii9", "V13"],
            ["IΔ7", "iii7", "vi7", "IV9"],
        ],
        "minor": [
            ["i9", "iv9", "bVII9", "bIII9"],
        ],
    },
    "edm": {
        "minor": [
            ["i", "VI", "III", "VII"],
            ["i", "i", "VI", "VII"],
            ["vi", "IV", "I", "V"],
        ],
    },
}

KEYS = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

NOTE_MAP = {
    "C": 60, "C#": 61, "D": 62, "Eb": 63, "E": 64, "F": 65,
    "F#": 66, "G": 67, "Ab": 68, "A": 69, "Bb": 70, "B": 71,
}

SCALE_INTERVALS = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
}


def music_generator(genre: str = "pop", key: str = "C", mode: str = "major",
                     bpm: int = 120, bars: int = 8,
                     create_midi: bool = False) -> Dict[str, Any]:
    """Generate chord progressions and optionally create a MIDI file."""
    genre = genre.lower()
    mode = mode.lower()
    if genre not in CHORD_PROGRESSIONS:
        genre = "pop"
    mode_progs = CHORD_PROGRESSIONS[genre].get(mode, CHORD_PROGRESSIONS[genre].get("major", []))
    if not mode_progs:
        mode_progs = [["I", "IV", "V", "I"]]

    progression = random.choice(mode_progs)
    # Repeat to fill bars
    full_progression = []
    while len(full_progression) < bars:
        full_progression.extend(progression)
    full_progression = full_progression[:bars]

    result = {
        "genre": genre,
        "key": key,
        "mode": mode,
        "bpm": bpm,
        "bars": bars,
        "progression": full_progression,
        "progression_str": " | ".join(full_progression),
        "suggested_rhythm": _suggest_rhythm(genre),
        "suggested_instruments": _suggest_instruments(genre),
    }

    if create_midi:
        midi_path = _create_midi(full_progression, key, mode, bpm, genre)
        result["midi_file"] = midi_path

    return result


def _suggest_rhythm(genre: str) -> str:
    rhythms = {
        "pop": "Straight 8ths, 4/4 time, strong backbeat on 2 & 4",
        "jazz": "Swing feel, walking bass, ride cymbal",
        "blues": "12/8 shuffle, walking bass line",
        "rock": "Driving 8ths, power chords, heavy kick/snare",
        "lofi": "Lazy swing, vinyl crackle, sidechain compression",
        "edm": "Four on the floor, syncopated hi-hats, big drops",
    }
    return rhythms.get(genre, "Standard 4/4")


def _suggest_instruments(genre: str) -> List[str]:
    instruments = {
        "pop": ["Piano/Keys", "Acoustic Guitar", "Synth Pad", "Bass", "Drums"],
        "jazz": ["Piano", "Upright Bass", "Drums (brushes)", "Saxophone", "Trumpet"],
        "blues": ["Electric Guitar", "Harmonica", "Bass", "Drums", "Organ"],
        "rock": ["Electric Guitar (distortion)", "Bass Guitar", "Drums", "Rhythm Guitar"],
        "lofi": ["Rhodes Piano", "Vinyl Crackle", "Muted Drums", "Soft Bass", "Ambient Pad"],
        "edm": ["Synth Lead", "Sub Bass", "808 Drums", "Pluck Synth", "Reverb Pad"],
    }
    return instruments.get(genre, ["Piano", "Bass", "Drums"])


def _create_midi(progression, key, mode, bpm, genre) -> str:
    """Create a simple MIDI file with the chord progression."""
    _ensure_workspace()
    filepath = os.path.join(WORKSPACE, f"chords_{genre}_{key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mid")

    # Simple MIDI file writer (Format 0)
    root = NOTE_MAP.get(key, 60)
    scale = SCALE_INTERVALS.get(mode, SCALE_INTERVALS["major"])
    ticks_per_beat = 480
    beats_per_bar = 4
    ticks_per_bar = ticks_per_beat * beats_per_bar

    # Degree to semitone offset (simplified)
    degree_map = {"I": 0, "i": 0, "II": 2, "ii": 2, "III": 4, "iii": 4,
                  "IV": 5, "iv": 5, "V": 7, "v": 7, "VI": 9, "vi": 9,
                  "VII": 11, "vii": 11, "bVII": 10, "bIII": 3, "bVI": 8}

    track_data = bytearray()

    # Tempo
    microseconds = int(60_000_000 / bpm)
    track_data += b'\x00\xff\x51\x03'
    track_data += microseconds.to_bytes(3, 'big')

    tick = 0
    for chord_name in progression:
        # Parse degree
        base = chord_name.rstrip("7945b#Δ ")
        for deg, semi in degree_map.items():
            if base.startswith(deg) or base == deg:
                offset = semi
                break
        else:
            offset = 0

        is_minor = base[0].islower() if base else False

        # Build chord notes
        chord_root = root + offset
        if is_minor:
            notes = [chord_root, chord_root + 3, chord_root + 7]
        else:
            notes = [chord_root, chord_root + 4, chord_root + 7]

        if "7" in chord_name:
            notes.append(chord_root + (10 if is_minor or "b" in chord_name else 11))

        # Note on events (delta=0 for simultaneous)
        for i, note in enumerate(notes):
            delta = ticks_per_bar if i == 0 and tick > 0 else 0
            track_data += _var_length(delta)
            track_data += bytes([0x90, note & 0x7F, 80])

        # Note off events after bar duration
        for i, note in enumerate(notes):
            delta = ticks_per_bar if i == 0 else 0
            track_data += _var_length(delta)
            track_data += bytes([0x80, note & 0x7F, 0])

        tick += ticks_per_bar

    # End of track
    track_data += b'\x00\xff\x2f\x00'

    # Write MIDI file
    with open(filepath, 'wb') as f:
        # Header
        f.write(b'MThd')
        f.write(struct.pack('>I', 6))  # header length
        f.write(struct.pack('>HHH', 0, 1, ticks_per_beat))
        # Track
        f.write(b'MTrk')
        f.write(struct.pack('>I', len(track_data)))
        f.write(track_data)

    return filepath


def _var_length(value: int) -> bytes:
    """Encode integer as MIDI variable-length quantity."""
    result = []
    result.append(value & 0x7F)
    value >>= 7
    while value:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.reverse()
    return bytes(result)


# ── Lyrics Generator ──────────────────────────────────────────────────────

def lyrics_generator(theme: str = "love", genre: str = "pop",
                     mood: str = "upbeat", verses: int = 2,
                     include_chorus: bool = True) -> Dict[str, Any]:
    """Generate song structure and lyric writing prompts."""
    structures = {
        "pop": ["Verse 1", "Pre-Chorus", "Chorus", "Verse 2", "Pre-Chorus", "Chorus", "Bridge", "Chorus"],
        "rock": ["Intro", "Verse 1", "Chorus", "Verse 2", "Chorus", "Solo", "Chorus", "Outro"],
        "hip_hop": ["Intro", "Verse 1 (16 bars)", "Hook", "Verse 2 (16 bars)", "Hook", "Verse 3 (16 bars)", "Hook", "Outro"],
        "ballad": ["Intro", "Verse 1", "Verse 2", "Chorus", "Verse 3", "Chorus", "Bridge", "Final Chorus"],
    }

    rhyme_schemes = {
        "pop": "ABAB or AABB",
        "rock": "ABAB",
        "hip_hop": "AABB (couplets) or ABAB",
        "ballad": "ABCB",
    }

    syllable_guides = {
        "pop": "8-10 syllables per line, keep it catchy",
        "rock": "6-10 syllables, raw and direct",
        "hip_hop": "12-16 syllables, internal rhymes, wordplay",
        "ballad": "8-12 syllables, flowing and emotional",
    }

    genre_key = genre.lower().replace("-", "_")
    structure = structures.get(genre_key, structures["pop"])

    return {
        "theme": theme,
        "genre": genre,
        "mood": mood,
        "song_structure": structure,
        "rhyme_scheme": rhyme_schemes.get(genre_key, "ABAB"),
        "syllable_guide": syllable_guides.get(genre_key, "8-10 syllables per line"),
        "writing_tips": [
            f"Start with a strong image or scene related to '{theme}'",
            "Use concrete sensory details instead of abstractions",
            f"Match the {mood} mood with word choice and rhythm",
            "Chorus should be memorable and sum up the core message",
            "Bridge should offer a new perspective or twist",
        ],
        "suggested_title_patterns": [
            f"'{theme.title()} [Metaphor]'",
            f"'When [event related to {theme}]'",
            f"'[Emotion] in the [Place]'",
        ],
    }


# ── Video Script Writer ───────────────────────────────────────────────────

def video_script(topic: str, duration_minutes: int = 10,
                 style: str = "educational", platform: str = "youtube") -> Dict[str, Any]:
    """Generate a video script structure with timing."""
    if platform == "tiktok" or platform == "reels":
        duration_minutes = min(duration_minutes, 3)

    sections_per_minute = 1.5
    num_sections = max(3, int(duration_minutes * sections_per_minute))
    words_per_minute = 150
    total_words = duration_minutes * words_per_minute

    style_hooks = {
        "educational": f"Did you know that {topic} is more complex than most people think?",
        "storytelling": f"Let me tell you a story about {topic} that changed everything...",
        "listicle": f"Here are the top things you need to know about {topic}.",
        "tutorial": f"By the end of this video, you'll master {topic}. Let's dive in.",
        "review": f"I spent weeks testing {topic}. Here's what I found.",
        "commentary": f"We need to talk about {topic}. This is getting out of hand.",
    }

    script = {
        "topic": topic,
        "platform": platform,
        "style": style,
        "duration_target": f"{duration_minutes} minutes",
        "word_count_target": total_words,
        "hook": style_hooks.get(style, f"Let's talk about {topic}."),
        "sections": [],
    }

    # Intro
    script["sections"].append({
        "name": "Hook + Intro",
        "duration": "0:00 - 0:30",
        "notes": [
            "Open with the hook — grab attention in first 5 seconds",
            "Briefly introduce yourself and the topic",
            "Preview what viewers will learn/see",
        ],
        "estimated_words": 75,
    })

    # Body sections
    remaining_time = duration_minutes * 60 - 60  # minus intro + outro
    section_time = remaining_time // (num_sections - 2)
    current_time = 30

    for i in range(num_sections - 2):
        start = current_time
        end = current_time + section_time
        script["sections"].append({
            "name": f"Section {i + 1}",
            "duration": f"{start // 60}:{start % 60:02d} - {end // 60}:{end % 60:02d}",
            "notes": [
                f"Key point {i + 1} about {topic}",
                "Include visual aid / B-roll suggestion",
                "Transition to next section",
            ],
            "estimated_words": int(section_time / 60 * words_per_minute),
        })
        current_time = end

    # Outro
    script["sections"].append({
        "name": "Outro + CTA",
        "duration": f"{current_time // 60}:{current_time % 60:02d} - {duration_minutes}:00",
        "notes": [
            "Summarize key takeaways",
            "Call to action (like, subscribe, comment)",
            "Tease next video",
        ],
        "estimated_words": 75,
    })

    script["seo_tips"] = {
        "title_formula": f"[Number/How To/Why] {topic} [Benefit/Year]",
        "description": f"Include '{topic}' in first 2 lines, add timestamps, relevant links",
        "tags": [topic] + topic.split()[:5],
        "thumbnail_tips": "High contrast, readable text, expressive face, 3 elements max",
    }

    return script


# ── Podcast Script ─────────────────────────────────────────────────────────

def podcast_script(topic: str, duration_minutes: int = 30,
                   format_type: str = "solo", guest_name: str = "") -> Dict[str, Any]:
    """Generate a podcast episode script/outline."""
    formats = {
        "solo": {
            "sections": [
                {"name": "Intro & Hook", "pct": 0.05},
                {"name": "Background & Context", "pct": 0.15},
                {"name": "Main Discussion Point 1", "pct": 0.20},
                {"name": "Main Discussion Point 2", "pct": 0.20},
                {"name": "Deep Dive / Hot Take", "pct": 0.20},
                {"name": "Actionable Takeaways", "pct": 0.10},
                {"name": "Outro & CTA", "pct": 0.10},
            ],
        },
        "interview": {
            "sections": [
                {"name": "Intro & Guest Introduction", "pct": 0.10},
                {"name": f"Guest Background — {guest_name or 'Guest'}", "pct": 0.10},
                {"name": "Core Questions (3-5)", "pct": 0.35},
                {"name": "Lightning Round / Fun Questions", "pct": 0.10},
                {"name": "Deep Dive on Key Topic", "pct": 0.20},
                {"name": "Guest Plugs & Outro", "pct": 0.15},
            ],
        },
        "debate": {
            "sections": [
                {"name": "Topic Introduction", "pct": 0.10},
                {"name": "Position A Argument", "pct": 0.20},
                {"name": "Position B Argument", "pct": 0.20},
                {"name": "Rebuttals", "pct": 0.20},
                {"name": "Audience Perspective", "pct": 0.15},
                {"name": "Conclusion & Verdict", "pct": 0.15},
            ],
        },
    }

    fmt = formats.get(format_type, formats["solo"])
    sections = []
    current_time = 0
    for sec in fmt["sections"]:
        sec_duration = int(duration_minutes * sec["pct"])
        sections.append({
            "name": sec["name"],
            "time": f"{current_time}:00 - {current_time + sec_duration}:00",
            "duration_minutes": sec_duration,
            "talking_points": [f"[Discuss aspect of '{topic}' relevant to {sec['name']}]"],
        })
        current_time += sec_duration

    return {
        "topic": topic,
        "format": format_type,
        "duration": f"{duration_minutes} minutes",
        "guest": guest_name or None,
        "sections": sections,
        "episode_title_ideas": [
            f"{topic}: Everything You Need to Know",
            f"The Truth About {topic}",
            f"Why {topic} Matters More Than Ever",
        ],
        "show_notes_template": {
            "summary": f"In this episode, we explore {topic}...",
            "timestamps": [f"{s['time'].split(' - ')[0]} — {s['name']}" for s in sections],
            "links": ["[Add relevant links]"],
        },
    }


# ── Image Prompt Generator ────────────────────────────────────────────────

def image_prompt(subject: str, style: str = "photorealistic",
                 platform: str = "midjourney", mood: str = "cinematic",
                 aspect_ratio: str = "16:9") -> Dict[str, Any]:
    """Generate optimized image prompts for AI image generators."""
    style_modifiers = {
        "photorealistic": "photorealistic, 8k UHD, DSLR, high quality, film grain, Fujifilm XT3",
        "anime": "anime style, cel shading, vibrant colors, Studio Ghibli inspired",
        "oil_painting": "oil painting, textured canvas, impasto technique, classical composition",
        "digital_art": "digital art, trending on ArtStation, concept art, highly detailed",
        "watercolor": "watercolor painting, soft edges, bleeding colors, wet on wet technique",
        "3d_render": "3D render, octane render, volumetric lighting, physically based rendering",
        "pixel_art": "pixel art, 16-bit style, retro gaming aesthetic, limited color palette",
        "comic": "comic book style, bold outlines, halftone dots, dynamic composition",
        "minimalist": "minimalist, clean lines, negative space, simple composition, flat design",
        "cyberpunk": "cyberpunk, neon lights, rain, futuristic, blade runner style, volumetric fog",
    }

    mood_modifiers = {
        "cinematic": "cinematic lighting, dramatic shadows, film still, anamorphic",
        "dreamy": "ethereal, soft focus, pastel colors, magical atmosphere",
        "dark": "dark moody, chiaroscuro, dramatic contrast, noir",
        "bright": "bright, vibrant colors, natural daylight, cheerful",
        "vintage": "vintage film, faded colors, nostalgic, retro",
        "epic": "epic scale, panoramic, awe-inspiring, grandiose",
    }

    style_mod = style_modifiers.get(style, style_modifiers["photorealistic"])
    mood_mod = mood_modifiers.get(mood, mood_modifiers["cinematic"])

    prompts = {}

    # Midjourney prompt
    prompts["midjourney"] = f"{subject}, {style_mod}, {mood_mod} --ar {aspect_ratio} --v 6 --q 2"

    # DALL-E prompt (more natural language)
    prompts["dalle"] = f"A {mood} {style.replace('_', ' ')} image of {subject}. {style_mod}. High quality, detailed."

    # Stable Diffusion prompt (with negative)
    prompts["stable_diffusion"] = {
        "positive": f"{subject}, {style_mod}, {mood_mod}, masterpiece, best quality",
        "negative": "ugly, blurry, low quality, deformed, disfigured, watermark, text, signature, out of frame",
        "cfg_scale": 7.5,
        "steps": 30,
    }

    # Return the preferred platform's prompt first
    primary = prompts.get(platform, prompts["midjourney"])

    return {
        "subject": subject,
        "style": style,
        "mood": mood,
        "primary_prompt": primary,
        "all_prompts": prompts,
        "tips": [
            "Add specific details about lighting, camera angle, and composition",
            "Use artist references sparingly but effectively",
            "Negative prompts help avoid common issues in SD",
            "For Midjourney, --stylize controls creativity vs prompt adherence",
        ],
    }


# ── Subtitle Generator ────────────────────────────────────────────────────

def subtitle_generator(text: str, duration_seconds: float = 60.0,
                       format_type: str = "srt",
                       words_per_subtitle: int = 8) -> Dict[str, Any]:
    """Generate subtitle/caption file from text content."""
    words = text.split()
    total_words = len(words)
    if total_words == 0:
        return {"error": "No text provided"}

    time_per_word = duration_seconds / total_words
    subtitles = []
    idx = 1
    current_time = 0.0

    for i in range(0, total_words, words_per_subtitle):
        chunk = words[i:i + words_per_subtitle]
        chunk_text = " ".join(chunk)
        chunk_duration = len(chunk) * time_per_word

        start = current_time
        end = current_time + chunk_duration

        subtitles.append({
            "index": idx,
            "start": start,
            "end": end,
            "text": chunk_text,
        })
        idx += 1
        current_time = end

    # Format output
    if format_type == "srt":
        srt_lines = []
        for sub in subtitles:
            start_str = _format_srt_time(sub["start"])
            end_str = _format_srt_time(sub["end"])
            srt_lines.append(f"{sub['index']}")
            srt_lines.append(f"{start_str} --> {end_str}")
            srt_lines.append(sub["text"])
            srt_lines.append("")
        output = "\n".join(srt_lines)
    elif format_type == "vtt":
        vtt_lines = ["WEBVTT", ""]
        for sub in subtitles:
            start_str = _format_vtt_time(sub["start"])
            end_str = _format_vtt_time(sub["end"])
            vtt_lines.append(f"{start_str} --> {end_str}")
            vtt_lines.append(sub["text"])
            vtt_lines.append("")
        output = "\n".join(vtt_lines)
    else:
        output = json.dumps(subtitles, indent=2)

    # Optionally save to file
    _ensure_workspace()
    ext = format_type if format_type in ("srt", "vtt") else "json"
    filepath = os.path.join(WORKSPACE, f"subtitles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}")
    with open(filepath, "w") as f:
        f.write(output)

    return {
        "subtitle_count": len(subtitles),
        "format": format_type,
        "duration": duration_seconds,
        "file_path": filepath,
        "preview": output[:500],
    }


def _format_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _format_vtt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


# ── Raw tools ──────────────────────────────────────────────────────────────

def _raw_tools() -> list:
    return [
        {
            "name": "music_generator",
            "description": "Generate chord progressions with optional MIDI file output. Supports pop, jazz, blues, rock, lofi, edm genres.",
            "parameters": {
                "type": "object",
                "properties": {
                    "genre": {"type": "string", "enum": ["pop", "jazz", "blues", "rock", "lofi", "edm"], "default": "pop"},
                    "key": {"type": "string", "default": "C", "description": "Musical key (C, D, E, etc)"},
                    "mode": {"type": "string", "enum": ["major", "minor"], "default": "major"},
                    "bpm": {"type": "integer", "default": 120},
                    "bars": {"type": "integer", "default": 8},
                    "create_midi": {"type": "boolean", "default": False},
                },
            },
            "function": music_generator,
        },
        {
            "name": "lyrics_generator",
            "description": "Generate song structure, writing prompts, and lyric guidelines for any genre.",
            "parameters": {
                "type": "object",
                "properties": {
                    "theme": {"type": "string", "default": "love"},
                    "genre": {"type": "string", "default": "pop"},
                    "mood": {"type": "string", "default": "upbeat"},
                    "verses": {"type": "integer", "default": 2},
                    "include_chorus": {"type": "boolean", "default": True},
                },
            },
            "function": lyrics_generator,
        },
        {
            "name": "video_script",
            "description": "Generate a structured video script with timing, sections, and SEO tips.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "duration_minutes": {"type": "integer", "default": 10},
                    "style": {"type": "string", "enum": ["educational", "storytelling", "listicle", "tutorial", "review", "commentary"], "default": "educational"},
                    "platform": {"type": "string", "enum": ["youtube", "tiktok", "reels"], "default": "youtube"},
                },
                "required": ["topic"],
            },
            "function": video_script,
        },
        {
            "name": "podcast_script",
            "description": "Generate a podcast episode outline with timing and talking points.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "duration_minutes": {"type": "integer", "default": 30},
                    "format_type": {"type": "string", "enum": ["solo", "interview", "debate"], "default": "solo"},
                    "guest_name": {"type": "string", "default": ""},
                },
                "required": ["topic"],
            },
            "function": podcast_script,
        },
        {
            "name": "image_prompt",
            "description": "Generate optimized image prompts for Midjourney, DALL-E, and Stable Diffusion.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string", "description": "What the image should depict"},
                    "style": {"type": "string", "enum": ["photorealistic", "anime", "oil_painting", "digital_art", "watercolor", "3d_render", "pixel_art", "comic", "minimalist", "cyberpunk"], "default": "photorealistic"},
                    "platform": {"type": "string", "enum": ["midjourney", "dalle", "stable_diffusion"], "default": "midjourney"},
                    "mood": {"type": "string", "enum": ["cinematic", "dreamy", "dark", "bright", "vintage", "epic"], "default": "cinematic"},
                    "aspect_ratio": {"type": "string", "default": "16:9"},
                },
                "required": ["subject"],
            },
            "function": image_prompt,
        },
        {
            "name": "subtitle_generator",
            "description": "Generate subtitle/caption files (SRT, VTT) from text with proper timing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The text content to create subtitles from"},
                    "duration_seconds": {"type": "number", "default": 60},
                    "format_type": {"type": "string", "enum": ["srt", "vtt", "json"], "default": "srt"},
                    "words_per_subtitle": {"type": "integer", "default": 8},
                },
                "required": ["text"],
            },
            "function": subtitle_generator,
        },
    ]


def get_tools():
    return adapt_tools(_raw_tools())
