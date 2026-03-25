"""Ouroboros — Film & Video Production tools."""

from __future__ import annotations
import json, os, logging
from datetime import datetime
from typing import Any, Dict, List
from ouroboros.tools._adapter import adapt_tools

log = logging.getLogger(__name__)
WORKSPACE = os.environ.get("OUROBOROS_WORKSPACE", "/tmp/ouroboros_content")


def _ensure_dir(subdir: str = "film"):
    path = f"{WORKSPACE}/{subdir}"
    os.makedirs(path, exist_ok=True)
    return path


def _save(data: dict, prefix: str) -> str:
    d = _ensure_dir()
    path = f"{d}/{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def screenplay_writer(title: str, genre: str = "drama", scenes: int = 5,
                       logline: str = "") -> Dict[str, Any]:
    script = {
        "title": title, "genre": genre, "logline": logline,
        "format": "industry_standard", "created": datetime.now().isoformat(),
        "scenes": [],
    }
    locations = ["INT. APARTMENT - NIGHT", "EXT. CITY STREET - DAY",
                 "INT. OFFICE - DAY", "EXT. ROOFTOP - NIGHT", "INT. CAR - MOVING - DAY"]
    for i in range(1, scenes + 1):
        loc = locations[(i - 1) % len(locations)]
        script["scenes"].append({
            "scene_number": i,
            "slug_line": loc,
            "action": f"Scene {i} action description. Set the visual tone for this beat.",
            "dialogue": [
                {"character": "PROTAGONIST", "parenthetical": "(determined)",
                 "line": f"Dialogue for scene {i} — drives the narrative forward."},
                {"character": "SUPPORTING", "parenthetical": "(cautious)",
                 "line": f"Response that creates tension or reveals character."},
            ],
            "transition": "CUT TO:" if i < scenes else "FADE OUT.",
        })
    script["saved_to"] = _save(script, "screenplay")
    return script


def shot_list(project: str, scene_count: int = 5,
              style: str = "cinematic") -> Dict[str, Any]:
    shot_types = ["WIDE", "MEDIUM", "CLOSE-UP", "EXTREME CLOSE-UP", "OVER-THE-SHOULDER"]
    angles = ["EYE LEVEL", "LOW ANGLE", "HIGH ANGLE", "DUTCH ANGLE", "BIRD'S EYE"]
    movements = ["STATIC", "PAN LEFT", "DOLLY IN", "TRACKING", "CRANE UP", "HANDHELD"]
    equipment = ["35mm Prime", "Zoom 24-70mm", "Steadicam", "Drone", "Slider"]
    result = {
        "project": project, "style": style, "created": datetime.now().isoformat(),
        "total_shots": scene_count * 3, "shots": [],
    }
    shot_num = 1
    for s in range(1, scene_count + 1):
        for j in range(3):
            result["shots"].append({
                "shot": shot_num, "scene": s,
                "type": shot_types[(shot_num - 1) % len(shot_types)],
                "angle": angles[(shot_num - 1) % len(angles)],
                "movement": movements[(shot_num - 1) % len(movements)],
                "equipment": equipment[(shot_num - 1) % len(equipment)],
                "description": f"Scene {s}, setup {j+1} — capture the key visual beat.",
                "duration_sec": 5 + (j * 3),
            })
            shot_num += 1
    result["saved_to"] = _save(result, "shotlist")
    return result


def storyboard(project: str, scenes: int = 5,
               aspect_ratio: str = "2.39:1") -> Dict[str, Any]:
    transitions = ["CUT", "DISSOLVE", "WIPE", "FADE", "MATCH CUT"]
    angles = ["Wide establishing", "Medium two-shot", "Close-up reaction",
              "POV shot", "Over-the-shoulder"]
    result = {
        "project": project, "aspect_ratio": aspect_ratio,
        "created": datetime.now().isoformat(), "panels": [],
    }
    panel = 1
    for s in range(1, scenes + 1):
        for f in range(3):
            result["panels"].append({
                "panel": panel, "scene": s, "frame": f + 1,
                "camera_angle": angles[(panel - 1) % len(angles)],
                "description": f"Scene {s} frame {f+1}: Visual composition showing key story moment.",
                "action_notes": "Character movement and blocking details.",
                "audio_notes": "Ambient sound or dialogue cue.",
                "transition_out": transitions[(panel - 1) % len(transitions)],
            })
            panel += 1
    result["saved_to"] = _save(result, "storyboard")
    return result


def production_budget(project: str, days: int = 5, crew_size: int = 10,
                      tier: str = "indie") -> Dict[str, Any]:
    multiplier = {"micro": 0.3, "indie": 1.0, "mid": 3.0, "studio": 10.0}.get(tier, 1.0)
    base = {
        "pre_production": {"script_development": 2000, "casting": 1500,
                           "location_scouting": 1000, "permits": 800},
        "crew": {"director": 500 * days, "dp": 400 * days,
                 "sound": 300 * days, "gaffer": 250 * days,
                 "additional_crew": 200 * days * max(0, crew_size - 4)},
        "equipment": {"camera_package": 500 * days, "lighting": 300 * days,
                      "sound_gear": 200 * days, "grip": 150 * days},
        "location": {"rental": 800 * days, "catering": 30 * crew_size * days,
                     "transportation": 200 * days},
        "post_production": {"editing": 3000, "color_grading": 2000,
                            "sound_mix": 2500, "music": 1500, "vfx": 2000},
        "contingency_10pct": 0,
    }
    for cat in base:
        if isinstance(base[cat], dict):
            for k in base[cat]:
                base[cat][k] = int(base[cat][k] * multiplier)
    subtotal = sum(v for cat in base.values() if isinstance(cat, dict)
                   for v in cat.values())
    base["contingency_10pct"] = int(subtotal * 0.1)
    result = {
        "project": project, "shoot_days": days, "crew_size": crew_size,
        "tier": tier, "budget": base,
        "total": subtotal + base["contingency_10pct"],
        "created": datetime.now().isoformat(),
    }
    result["saved_to"] = _save(result, "budget")
    return result


def casting_breakdown(project: str, characters: int = 4,
                      genre: str = "drama") -> Dict[str, Any]:
    archetypes = [
        {"role": "Lead", "age_range": "25-35", "type": "Protagonist",
         "traits": "Complex, driven, relatable"},
        {"role": "Supporting", "age_range": "30-50", "type": "Mentor/Ally",
         "traits": "Wise, grounded, protective"},
        {"role": "Antagonist", "age_range": "35-55", "type": "Antagonist",
         "traits": "Charismatic, calculating, layered"},
        {"role": "Supporting", "age_range": "20-30", "type": "Catalyst",
         "traits": "Energetic, unpredictable, loyal"},
        {"role": "Featured", "age_range": "40-60", "type": "Authority",
         "traits": "Commanding, pragmatic"},
    ]
    result = {
        "project": project, "genre": genre,
        "created": datetime.now().isoformat(), "characters": [],
    }
    for i in range(min(characters, len(archetypes))):
        a = archetypes[i]
        result["characters"].append({
            "character_name": f"Character_{i+1}",
            "role_type": a["role"], "age_range": a["age_range"],
            "character_type": a["type"], "traits": a["traits"],
            "scenes_appearing": list(range(1, characters + 1)),
            "description": f"{a['type']} role for {genre} — {a['traits']}.",
            "audition_sides": f"Scene {i+1} monologue or key dialogue.",
        })
    result["saved_to"] = _save(result, "casting")
    return result


def shooting_schedule(project: str, shoot_days: int = 3,
                      scenes: int = 8) -> Dict[str, Any]:
    locations = ["Studio A", "Downtown Exterior", "Residential Interior",
                 "Park/Outdoor", "Office Building"]
    result = {
        "project": project, "total_days": shoot_days,
        "created": datetime.now().isoformat(), "schedule": [],
    }
    scenes_per_day = max(1, scenes // shoot_days)
    scene_idx = 1
    for day in range(1, shoot_days + 1):
        day_plan = {
            "day": day, "call_time": "06:00", "wrap_time": "18:00",
            "location": locations[(day - 1) % len(locations)], "scenes": [],
        }
        for _ in range(scenes_per_day):
            if scene_idx > scenes:
                break
            day_plan["scenes"].append({
                "scene": scene_idx, "est_hours": round(10 / scenes_per_day, 1),
                "cast_required": ["Lead"] + (["Supporting"] if scene_idx % 2 == 0 else []),
                "equipment_notes": "Standard camera and lighting package.",
            })
            scene_idx += 1
        remaining = scenes - scene_idx + 1
        if day == shoot_days and remaining > 0:
            for r in range(remaining):
                day_plan["scenes"].append({
                    "scene": scene_idx + r, "est_hours": 1.5,
                    "cast_required": ["Lead"], "equipment_notes": "Minimal setup.",
                })
        day_plan["meal_break"] = "12:00-13:00"
        result["schedule"].append(day_plan)
    result["saved_to"] = _save(result, "schedule")
    return result


def color_grading(genre: str = "noir", mood: str = "dark",
                  format: str = "digital") -> Dict[str, Any]:
    palettes = {
        "noir": {"shadows": "#0a0a14", "midtones": "#2a2a3e", "highlights": "#c8c8d0",
                 "contrast": "high", "saturation": "desaturated",
                 "notes": "Deep blacks, cool blue-grey midtones, crushed shadows."},
        "warm": {"shadows": "#1a0f0a", "midtones": "#8b6914", "highlights": "#ffe8b0",
                 "contrast": "medium", "saturation": "rich",
                 "notes": "Golden hour warmth, amber midtones, soft highlights."},
        "cold": {"shadows": "#0a1420", "midtones": "#3a5a7a", "highlights": "#d0e0f0",
                 "contrast": "medium-high", "saturation": "muted",
                 "notes": "Steel blue tones, clinical feel, high-key lighting."},
        "vintage": {"shadows": "#1a1410", "midtones": "#7a6a50", "highlights": "#e8dcc8",
                    "contrast": "low", "saturation": "faded",
                    "notes": "Lifted blacks, faded warm tones, grain overlay."},
    }
    palette = palettes.get(genre, palettes["noir"])
    result = {
        "genre": genre, "mood": mood, "format": format,
        "created": datetime.now().isoformat(),
        "lut_description": palette,
        "workflow": [
            "1. Apply base correction (exposure, white balance)",
            "2. Set primary color wheels (shadows/mids/highlights)",
            "3. Apply power windows for selective grading",
            "4. Add film grain and halation if vintage",
            "5. Final contrast and saturation pass",
        ],
        "reference_films": {
            "noir": ["Blade Runner", "Se7en", "The Third Man"],
            "warm": ["Amelie", "The Grand Budapest Hotel", "Mad Max: Fury Road"],
            "cold": ["The Revenant", "Zodiac", "Ex Machina"],
            "vintage": ["Moonlight", "Carol", "The Master"],
        }.get(genre, []),
    }
    result["saved_to"] = _save(result, "colorgrade")
    return result


def sound_design(project: str, scenes: int = 5,
                 genre: str = "drama") -> Dict[str, Any]:
    result = {
        "project": project, "genre": genre,
        "created": datetime.now().isoformat(), "sound_map": [],
    }
    ambience_pool = ["Room tone", "City hum", "Wind/nature", "Crowd murmur", "Silence"]
    for s in range(1, scenes + 1):
        result["sound_map"].append({
            "scene": s,
            "ambience": ambience_pool[(s - 1) % len(ambience_pool)],
            "foley": ["Footsteps", "Door open/close", "Object handling"],
            "sfx": f"Scene {s} specific effect — match to key visual moment.",
            "music_cue": {
                "type": "underscore" if s % 2 == 0 else "source",
                "mood": "tension" if s > scenes // 2 else "establishing",
                "in_point": "Scene start" if s == 1 else "After first beat",
                "out_point": "Fade under dialogue" if s < scenes else "Hard out",
            },
            "dialogue_notes": "Clean production audio preferred. ADR if needed.",
        })
    result["mix_notes"] = {
        "levels": {"dialogue": "-12dB to -6dB", "music": "-24dB to -18dB",
                   "sfx": "-18dB to -12dB", "ambience": "-30dB to -24dB"},
        "delivery": ["Stereo mix", "5.1 surround", "M&E stem"],
    }
    result["saved_to"] = _save(result, "sounddesign")
    return result


def distribution_strategy(project: str, budget_tier: str = "indie",
                          runtime_min: int = 90, genre: str = "drama") -> Dict[str, Any]:
    festivals = {
        "tier_a": ["Sundance", "TIFF", "Cannes", "Venice", "Berlin"],
        "tier_b": ["Tribeca", "SXSW", "Telluride", "Locarno"],
        "regional": ["Local film festivals", "Genre-specific festivals"],
    }
    premiere = festivals["tier_a"][:3] if budget_tier != "micro" else festivals["tier_b"][:2]
    secondary = festivals["tier_b"] if budget_tier != "micro" else festivals["regional"]
    windows = [("Festival Run", "Months 1-6", "Build buzz and reviews"),
               ("Theatrical", "Months 6-9", "Key markets only"),
               ("TVOD", "Months 9-12", "iTunes, Google Play, Vimeo OD"),
               ("SVOD", "Months 12-18", "Netflix, MUBI, Criterion Channel"),
               ("AVOD/Free", "Months 18+", "Tubi, YouTube, Pluto TV")]
    result = {
        "project": project, "runtime": f"{runtime_min} min",
        "budget_tier": budget_tier, "genre": genre, "created": datetime.now().isoformat(),
        "festival_strategy": {"premiere_targets": premiere, "secondary": secondary,
                              "submission_timeline": "6-8 months before premiere target"},
        "distribution_windows": [{"window": w, "timeline": t, "notes": n} for w, t, n in windows],
        "marketing": {
            "deliverables": ["Trailer (90s + 30s)", "Poster", "EPK", "Stills (min 20)", "BTS featurette"],
            "channels": ["Social media", "Press screenings", "Film blogs", "Podcasts", "Community screenings"],
            "estimated_p_and_a": {"micro": 5000, "indie": 25000, "mid": 150000, "studio": 1000000}.get(budget_tier, 25000),
        },
    }
    result["saved_to"] = _save(result, "distribution")
    return result


def video_editor_guide(project: str, style: str = "narrative",
                       software: str = "davinci_resolve") -> Dict[str, Any]:
    cuts = [("Hard Cut", "Standard transitions"), ("J-Cut", "Audio leads video"),
            ("L-Cut", "Video leads audio"), ("Match Cut", "Visual/thematic similarity"),
            ("Jump Cut", "Time compression"), ("Smash Cut", "Abrupt tonal shift")]
    cut_types = [{"name": n, "use": u} for n, u in cuts]
    pacing = {
        "narrative": {"avg_shot_length": "4-6s", "rhythm": "Varies with tension arc"},
        "commercial": {"avg_shot_length": "1.5-3s", "rhythm": "Fast, punchy"},
        "documentary": {"avg_shot_length": "5-10s", "rhythm": "Measured, observational"},
        "music_video": {"avg_shot_length": "1-2s", "rhythm": "Beat-synced"},
    }
    result = {
        "project": project, "style": style, "software": software,
        "created": datetime.now().isoformat(),
        "cut_types": cut_types,
        "pacing": pacing.get(style, pacing["narrative"]),
        "color_workflow": ["Organize timeline", "Rough cut assembly", "Fine cut (pacing)",
                          "Sound design pass", "Color grading", "Export master"],
        "transitions": ["Dissolve", "Fade to black", "Wipe", "Iris"],
        "keyboard_shortcuts": {
            "davinci_resolve": {"blade": "B", "trim": "T", "ripple_delete": "Shift+Del", "render": "Ctrl+Shift+R"},
            "premiere_pro": {"blade": "C", "trim": "T", "ripple_delete": "Shift+Del", "render": "Ctrl+M"},
        }.get(software, {}),
    }
    result["saved_to"] = _save(result, "editguide")
    return result


def _raw_tools() -> list:
    return [
        {"name": "screenplay_writer",
         "description": "Generate screenplay in proper format with INT/EXT slug lines, action, dialogue, and parentheticals.",
         "parameters": {"type": "object", "properties": {
             "title": {"type": "string"}, "genre": {"type": "string", "default": "drama"},
             "scenes": {"type": "integer", "default": 5}, "logline": {"type": "string", "default": ""},
         }, "required": ["title"]}, "function": screenplay_writer},
        {"name": "shot_list",
         "description": "Generate shot lists with shot type, angle, movement, description, and equipment notes.",
         "parameters": {"type": "object", "properties": {
             "project": {"type": "string"}, "scene_count": {"type": "integer", "default": 5},
             "style": {"type": "string", "default": "cinematic"},
         }, "required": ["project"]}, "function": shot_list},
        {"name": "storyboard",
         "description": "Generate text-based storyboard with camera angles, compositions, and transitions per panel.",
         "parameters": {"type": "object", "properties": {
             "project": {"type": "string"}, "scenes": {"type": "integer", "default": 5},
             "aspect_ratio": {"type": "string", "default": "2.39:1"},
         }, "required": ["project"]}, "function": storyboard},
        {"name": "production_budget",
         "description": "Estimate film/video production budget by category: crew, equipment, location, post-production.",
         "parameters": {"type": "object", "properties": {
             "project": {"type": "string"}, "days": {"type": "integer", "default": 5},
             "crew_size": {"type": "integer", "default": 10},
             "tier": {"type": "string", "enum": ["micro", "indie", "mid", "studio"], "default": "indie"},
         }, "required": ["project"]}, "function": production_budget},
        {"name": "casting_breakdown",
         "description": "Generate character breakdowns for casting with age, type, description, and scene appearances.",
         "parameters": {"type": "object", "properties": {
             "project": {"type": "string"}, "characters": {"type": "integer", "default": 4},
             "genre": {"type": "string", "default": "drama"},
         }, "required": ["project"]}, "function": casting_breakdown},
        {"name": "shooting_schedule",
         "description": "Generate shooting schedule organized by location and day with call times and cast requirements.",
         "parameters": {"type": "object", "properties": {
             "project": {"type": "string"}, "shoot_days": {"type": "integer", "default": 3},
             "scenes": {"type": "integer", "default": 8},
         }, "required": ["project"]}, "function": shooting_schedule},
        {"name": "color_grading",
         "description": "Generate color grading LUT descriptions and mood references by genre (noir, warm, cold, vintage).",
         "parameters": {"type": "object", "properties": {
             "genre": {"type": "string", "enum": ["noir", "warm", "cold", "vintage"], "default": "noir"},
             "mood": {"type": "string", "default": "dark"},
             "format": {"type": "string", "default": "digital"},
         }}, "function": color_grading},
        {"name": "sound_design",
         "description": "Generate sound design plans with foley, ambience, SFX, and music cues per scene.",
         "parameters": {"type": "object", "properties": {
             "project": {"type": "string"}, "scenes": {"type": "integer", "default": 5},
             "genre": {"type": "string", "default": "drama"},
         }, "required": ["project"]}, "function": sound_design},
        {"name": "distribution_strategy",
         "description": "Generate film distribution plan covering festivals, streaming, theatrical, VOD, and marketing.",
         "parameters": {"type": "object", "properties": {
             "project": {"type": "string"}, "budget_tier": {"type": "string", "default": "indie"},
             "runtime_min": {"type": "integer", "default": 90},
             "genre": {"type": "string", "default": "drama"},
         }, "required": ["project"]}, "function": distribution_strategy},
        {"name": "video_editor_guide",
         "description": "Generate editing guides with cut types, pacing, transitions, and color workflow.",
         "parameters": {"type": "object", "properties": {
             "project": {"type": "string"},
             "style": {"type": "string", "enum": ["narrative", "commercial", "documentary", "music_video"], "default": "narrative"},
             "software": {"type": "string", "enum": ["davinci_resolve", "premiere_pro"], "default": "davinci_resolve"},
         }, "required": ["project"]}, "function": video_editor_guide},
    ]


def get_tools():
    return adapt_tools(_raw_tools())
