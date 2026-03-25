"""Ouroboros — Web Design tools (10 tools, compact)."""

from __future__ import annotations

import colorsys
import hashlib
import json
import math
import re
import textwrap
from typing import Any, Dict, List

from ouroboros.tools._adapter import adapt_tools


def _hex(r, g, b):
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


def _hsl_to_hex(h, s, l):
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return _hex(r, g, b)


def _contrast_ratio(hex1, hex2):
    def lum(h):
        r, g, b = int(h[1:3], 16)/255, int(h[3:5], 16)/255, int(h[5:7], 16)/255
        cs = [c/12.92 if c <= 0.03928 else ((c+0.055)/1.055)**2.4 for c in (r, g, b)]
        return 0.2126*cs[0] + 0.7152*cs[1] + 0.0722*cs[2]
    l1, l2 = lum(hex1), lum(hex2)
    if l1 < l2: l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


# ── Tool handlers ──────────────────────────────────────────────────────────

def _generate_website(title="My Website", description="A modern website", sections=None, style="modern"):
    """Generate full HTML/CSS/JS responsive page."""
    sections = sections or ["hero", "features", "about", "contact"]
    fonts = {"modern": "'Inter', sans-serif", "classic": "'Georgia', serif", "minimal": "'Helvetica', sans-serif"}
    font = fonts.get(style, fonts["modern"])
    section_html = []
    for s in sections:
        sid = s.lower().replace(" ", "-")
        section_html.append(f'  <section id="{sid}" class="section"><div class="container"><h2>{s.title()}</h2><p>Content for {s} section.</p></div></section>')
    return {
        "html": textwrap.dedent(f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:{font};line-height:1.6;color:#333}}
.container{{max-width:1200px;margin:0 auto;padding:0 20px}}
nav{{background:#1a1a2e;color:#fff;padding:1rem 0;position:sticky;top:0;z-index:100}}
nav .container{{display:flex;justify-content:space-between;align-items:center}}
nav a{{color:#fff;text-decoration:none;margin-left:1.5rem}}
.hero{{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:6rem 0;text-align:center}}
.hero h1{{font-size:3rem;margin-bottom:1rem}}
.section{{padding:4rem 0}}
.section:nth-child(even){{background:#f8f9fa}}
.section h2{{font-size:2rem;margin-bottom:1.5rem;text-align:center}}
.btn{{display:inline-block;padding:12px 30px;background:#667eea;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:1rem;text-decoration:none}}
.btn:hover{{background:#5a6fd6}}
footer{{background:#1a1a2e;color:#fff;padding:2rem 0;text-align:center}}
@media(max-width:768px){{.hero h1{{font-size:2rem}}.hero{{padding:3rem 0}}}}
</style>
</head>
<body>
<nav><div class="container"><strong>{title}</strong><div>{''.join(f'<a href="#{s.lower().replace(" ","-")}">{s.title()}</a>' for s in sections)}</div></div></nav>
<header class="hero"><div class="container"><h1>{title}</h1><p>{description}</p><br><a href="#" class="btn">Get Started</a></div></header>
{chr(10).join(section_html)}
<footer><div class="container"><p>&copy; 2024 {title}. All rights reserved.</p></div></footer>
<script>
document.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener('click',e=>{{e.preventDefault();document.querySelector(a.getAttribute('href'))?.scrollIntoView({{behavior:'smooth'}})}}));
</script>
</body>
</html>"""),
        "sections": sections, "style": style
    }


def _landing_page(product="Product", tagline="The best solution", features=None, cta_text="Start Free Trial", pricing=None):
    """Generate conversion-optimized landing page."""
    features = features or ["Fast", "Secure", "Scalable"]
    pricing = pricing or [{"name": "Free", "price": "$0", "features": ["Basic"]}, {"name": "Pro", "price": "$29", "features": ["Everything"]}]
    feat_cards = "\n".join(f'<div class="card"><h3>{f}</h3><p>Experience the power of {f.lower()}.</p></div>' for f in features)
    price_cards = "\n".join(f'<div class="price-card"><h3>{p["name"]}</h3><div class="price">{p["price"]}</div><ul>{"".join(f"<li>{x}</li>" for x in p["features"])}</ul><a href="#" class="btn">{cta_text}</a></div>' for p in pricing)
    return {"html": textwrap.dedent(f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{product}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Inter',sans-serif;color:#333}}
.hero{{background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;padding:6rem 2rem;text-align:center}}
.hero h1{{font-size:3.5rem;margin-bottom:1rem}}
.hero p{{font-size:1.25rem;opacity:0.9;margin-bottom:2rem}}
.btn{{display:inline-block;padding:14px 36px;background:#fff;color:#6366f1;border-radius:8px;font-weight:700;text-decoration:none;font-size:1.1rem}}
.btn:hover{{transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,0.2)}}
.features{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:2rem;padding:4rem 2rem;max-width:1200px;margin:0 auto}}
.card{{padding:2rem;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.1);text-align:center}}
.card h3{{color:#6366f1;margin-bottom:0.5rem}}
.pricing{{display:flex;justify-content:center;gap:2rem;padding:4rem 2rem;flex-wrap:wrap}}
.price-card{{border:2px solid #e5e7eb;border-radius:12px;padding:2rem;width:280px;text-align:center}}
.price-card .price{{font-size:2.5rem;font-weight:700;color:#6366f1;margin:1rem 0}}
.price-card ul{{list-style:none;margin:1rem 0}}
.price-card li{{padding:0.5rem 0;border-bottom:1px solid #f3f4f6}}
.price-card .btn{{background:#6366f1;color:#fff;margin-top:1rem}}
footer{{background:#111827;color:#9ca3af;text-align:center;padding:2rem}}
</style>
</head>
<body>
<section class="hero"><h1>{product}</h1><p>{tagline}</p><a href="#pricing" class="btn">{cta_text}</a></section>
<section class="features">{feat_cards}</section>
<section id="pricing"><h2 style="text-align:center;font-size:2rem;margin:2rem">Pricing</h2><div class="pricing">{price_cards}</div></section>
<footer><p>&copy; 2024 {product}</p></footer>
</body>
</html>"""), "product": product}


def _react_component(name="MyComponent", props=None, state=None, style_type="css-modules"):
    """Generate React functional component with hooks."""
    props = props or []
    state = state or {}
    props_type = ", ".join(f"{p}: string" for p in props) if props else ""
    props_destructure = ", ".join(props) if props else ""
    state_lines = "\n".join(f"  const [{k}, set{k[0].upper()+k[1:]}] = useState({json.dumps(v)});" for k, v in state.items())
    imports = ["import React", "{ useState }"] if state else ["import React"]
    return {"component": textwrap.dedent(f"""\
import React, {{ useState, useEffect }} from 'react';
{f"import styles from './{name}.module.css';" if style_type == "css-modules" else ""}

interface {name}Props {{
  {props_type}
}}

const {name}: React.FC<{name}Props> = ({{{ {props_destructure} }}}) => {{
{state_lines}

  useEffect(() => {{
    // Side effect logic
    return () => {{}};
  }}, []);

  return (
    <div className={{styles.container}}>
      <h2>{name}</h2>
      {chr(10).join(f"      <p>{{{p}}}</p>" for p in props)}
    </div>
  );
}};

export default {name};
"""), "css": f".container {{\n  padding: 1rem;\n}}", "name": name}


def _color_palette(base_color="#3b82f6", mode="complementary", count=5):
    """Generate color scheme."""
    r, g, b = int(base_color[1:3], 16)/255, int(base_color[3:5], 16)/255, int(base_color[5:7], 16)/255
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    colors = [base_color]
    if mode == "complementary":
        for i in range(1, count):
            nh = (h + 0.5 + i * 0.05) % 1.0
            colors.append(_hsl_to_hex(nh, s, l))
    elif mode == "analogous":
        for i in range(1, count):
            nh = (h + i * 0.083) % 1.0
            colors.append(_hsl_to_hex(nh, s, l))
    elif mode == "triadic":
        for i in range(1, count):
            nh = (h + i / 3) % 1.0
            colors.append(_hsl_to_hex(nh, s, l))
    elif mode == "monochromatic":
        for i in range(1, count):
            nl = max(0.1, min(0.9, l + (i - count//2) * 0.15))
            colors.append(_hsl_to_hex(h, s, nl))
    else:
        for i in range(1, count):
            nh = (h + i / count) % 1.0
            colors.append(_hsl_to_hex(nh, s, l))
    css_vars = "\n".join(f"  --color-{i}: {c};" for i, c in enumerate(colors))
    return {"colors": colors, "mode": mode, "css": f":root {{\n{css_vars}\n}}"}


def _css_animation(name="fadeIn", type="fade", duration="0.3s", easing="ease", iterations="1"):
    """Generate CSS keyframe animation."""
    keyframes_map = {
        "fade": "from{opacity:0}to{opacity:1}",
        "slide-up": "from{transform:translateY(20px);opacity:0}to{transform:translateY(0);opacity:1}",
        "slide-down": "from{transform:translateY(-20px);opacity:0}to{transform:translateY(0);opacity:1}",
        "scale": "from{transform:scale(0.8);opacity:0}to{transform:scale(1);opacity:1}",
        "rotate": "from{transform:rotate(0deg)}to{transform:rotate(360deg)}",
        "bounce": "0%,100%{transform:translateY(0)}50%{transform:translateY(-20px)}",
        "shake": "0%,100%{transform:translateX(0)}25%{transform:translateX(-10px)}75%{transform:translateX(10px)}",
        "pulse": "0%,100%{transform:scale(1)}50%{transform:scale(1.05)}",
    }
    kf = keyframes_map.get(type, keyframes_map["fade"])
    css = f"@keyframes {name}{{{kf}}}\n.{name}{{animation:{name} {duration} {easing} {iterations};}}"
    return {"css": css, "name": name, "type": type, "usage": f'<div class="{name}">Animated</div>'}


def _dark_mode_theme(primary="#6366f1", background_light="#ffffff", background_dark="#0f172a", text_light="#1e293b", text_dark="#e2e8f0"):
    """Generate CSS custom properties for light/dark toggle."""
    return {"css": textwrap.dedent(f"""\
:root {{
  --bg: {background_light};
  --text: {text_light};
  --primary: {primary};
  --surface: #f8fafc;
  --border: #e2e8f0;
}}
[data-theme="dark"] {{
  --bg: {background_dark};
  --text: {text_dark};
  --primary: {primary};
  --surface: #1e293b;
  --border: #334155;
}}
body {{ background: var(--bg); color: var(--text); transition: background 0.3s, color 0.3s; }}
"""), "js": 'const toggle=()=>{document.documentElement.dataset.theme=document.documentElement.dataset.theme==="dark"?"light":"dark"};',
    "toggle_html": '<button onclick="toggle()" aria-label="Toggle dark mode">🌓</button>'}


def _meta_tags(title="Page Title", description="Page description", url="https://example.com", image="https://example.com/og.png", type="website", twitter_handle=""):
    """Generate Open Graph + Twitter Cards + JSON-LD."""
    og = f'<meta property="og:title" content="{title}">\n<meta property="og:description" content="{description}">\n<meta property="og:image" content="{image}">\n<meta property="og:url" content="{url}">\n<meta property="og:type" content="{type}">'
    tw = f'<meta name="twitter:card" content="summary_large_image">\n<meta name="twitter:title" content="{title}">\n<meta name="twitter:description" content="{description}">\n<meta name="twitter:image" content="{image}">'
    if twitter_handle:
        tw += f'\n<meta name="twitter:site" content="@{twitter_handle}">'
    jsonld = json.dumps({"@context": "https://schema.org", "@type": "WebPage", "name": title, "description": description, "url": url, "image": image}, indent=2)
    return {"open_graph": og, "twitter_cards": tw, "json_ld": f'<script type="application/ld+json">\n{jsonld}\n</script>', "all": f"{og}\n{tw}\n" + f'<script type="application/ld+json">\n{jsonld}\n</script>'}


def _gradient_gen(type="linear", colors=None, angle=135, shape="circle"):
    """Generate CSS gradient."""
    colors = colors or ["#667eea", "#764ba2"]
    color_str = ", ".join(colors)
    if type == "linear":
        grad = f"linear-gradient({angle}deg, {color_str})"
    elif type == "radial":
        grad = f"radial-gradient({shape}, {color_str})"
    elif type == "conic":
        grad = f"conic-gradient(from {angle}deg, {color_str})"
    else:
        grad = f"linear-gradient({angle}deg, {color_str})"
    return {"css": f"background: {grad};", "gradient": grad, "colors": colors,
            "full_css": f".gradient-bg {{\n  background: {grad};\n  min-height: 100vh;\n}}"}


def _accessibility_check(html_content=""):
    """Run WCAG audit on HTML string."""
    issues = []
    if not html_content:
        return {"issues": [], "score": 100, "summary": "No HTML provided"}
    imgs = re.findall(r'<img\b[^>]*>', html_content, re.I)
    for img in imgs:
        if 'alt=' not in img.lower():
            issues.append({"severity": "error", "rule": "WCAG 1.1.1", "message": f"Image missing alt attribute: {img[:60]}"})
    links = re.findall(r'<a\b[^>]*>(.*?)</a>', html_content, re.I | re.S)
    for text in links:
        clean = re.sub(r'<[^>]+>', '', text).strip()
        if clean.lower() in ("click here", "here", "link", "read more", ""):
            issues.append({"severity": "warning", "rule": "WCAG 2.4.4", "message": f"Non-descriptive link text: '{clean}'"})
    if '<html' in html_content and 'lang=' not in html_content.split('>')[0]:
        issues.append({"severity": "error", "rule": "WCAG 3.1.1", "message": "Missing lang attribute on <html>"})
    forms = re.findall(r'<input\b[^>]*>', html_content, re.I)
    for f in forms:
        fid = re.search(r'id=["\']([^"\']+)', f)
        if fid and f'for="{fid.group(1)}"' not in html_content and f"for='{fid.group(1)}'" not in html_content:
            issues.append({"severity": "warning", "rule": "WCAG 1.3.1", "message": f"Input may lack associated label: {f[:60]}"})
    if not re.search(r'<h1\b', html_content, re.I):
        issues.append({"severity": "warning", "rule": "WCAG 1.3.1", "message": "No <h1> found on page"})
    headings = [int(m) for m in re.findall(r'<h(\d)\b', html_content, re.I)]
    for i in range(1, len(headings)):
        if headings[i] > headings[i-1] + 1:
            issues.append({"severity": "warning", "rule": "WCAG 1.3.1", "message": f"Heading level skip: h{headings[i-1]} to h{headings[i]}"})
    cr_issues = re.findall(r'color:\s*(#[0-9a-fA-F]{6})', html_content)
    bg_issues = re.findall(r'background(?:-color)?:\s*(#[0-9a-fA-F]{6})', html_content)
    if cr_issues and bg_issues:
        ratio = _contrast_ratio(cr_issues[0], bg_issues[0])
        if ratio < 4.5:
            issues.append({"severity": "error", "rule": "WCAG 1.4.3", "message": f"Low contrast ratio ({ratio:.1f}:1) between {cr_issues[0]} and {bg_issues[0]}"})
    errors = sum(1 for i in issues if i["severity"] == "error")
    warnings = sum(1 for i in issues if i["severity"] == "warning")
    score = max(0, 100 - errors * 15 - warnings * 5)
    return {"issues": issues, "score": score, "errors": errors, "warnings": warnings,
            "summary": f"Score: {score}/100 — {errors} errors, {warnings} warnings"}


def _tailwind_component(type="card", variant="default", dark_mode=True):
    """Generate Tailwind CSS component."""
    components = {
        "card": '<div class="bg-white rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow{dm}"><h3 class="text-xl font-semibold text-gray-800{dmt}">Card Title</h3><p class="mt-2 text-gray-600{dmt2}">Card content goes here.</p><button class="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors">Action</button></div>',
        "navbar": '<nav class="bg-white shadow-sm px-6 py-4{dm}"><div class="max-w-7xl mx-auto flex justify-between items-center"><a href="#" class="text-xl font-bold text-indigo-600">Brand</a><div class="hidden md:flex space-x-6"><a href="#" class="text-gray-600 hover:text-indigo-600 transition-colors">Home</a><a href="#" class="text-gray-600 hover:text-indigo-600 transition-colors">About</a><a href="#" class="text-gray-600 hover:text-indigo-600 transition-colors">Contact</a></div></div></nav>',
        "hero": '<section class="bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-20 px-6"><div class="max-w-4xl mx-auto text-center"><h1 class="text-5xl font-bold mb-6">Hero Title</h1><p class="text-xl opacity-90 mb-8">Subtitle text goes here.</p><a href="#" class="inline-block px-8 py-3 bg-white text-indigo-600 font-semibold rounded-lg hover:bg-gray-100 transition-colors">Get Started</a></div></section>',
        "form": '<form class="max-w-md mx-auto bg-white p-8 rounded-xl shadow-md space-y-4{dm}"><div><label class="block text-sm font-medium text-gray-700 mb-1">Email</label><input type="email" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent" placeholder="you@example.com"></div><div><label class="block text-sm font-medium text-gray-700 mb-1">Message</label><textarea class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent" rows="4"></textarea></div><button type="submit" class="w-full py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors">Submit</button></form>',
        "button": '<button class="px-6 py-3 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 active:bg-indigo-800 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2{dm}">Click Me</button>',
    }
    dm_classes = {
        "dm": " dark:bg-gray-800" if dark_mode else "",
        "dmt": " dark:text-white" if dark_mode else "",
        "dmt2": " dark:text-gray-300" if dark_mode else "",
    }
    raw = components.get(type, components["card"])
    result = raw.format(**dm_classes)
    return {"html": result, "type": type, "variant": variant, "dark_mode": dark_mode,
            "tip": "Add 'dark' class to <html> to activate dark mode" if dark_mode else ""}


# ── Registry ───────────────────────────────────────────────────────────────

def _raw_tools():
    return [
        {"name": "generate_website", "description": "Generate a full HTML/CSS/JS responsive website from a description",
         "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "description": {"type": "string"}, "sections": {"type": "array", "items": {"type": "string"}}, "style": {"type": "string", "enum": ["modern", "classic", "minimal"]}}, "required": []},
         "function": _generate_website},
        {"name": "landing_page", "description": "Generate a conversion-optimized landing page with hero, CTA, and pricing",
         "parameters": {"type": "object", "properties": {"product": {"type": "string"}, "tagline": {"type": "string"}, "features": {"type": "array", "items": {"type": "string"}}, "cta_text": {"type": "string"}, "pricing": {"type": "array"}}, "required": []},
         "function": _landing_page},
        {"name": "react_component", "description": "Generate a React functional component with TypeScript and hooks",
         "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "props": {"type": "array", "items": {"type": "string"}}, "state": {"type": "object"}, "style_type": {"type": "string", "enum": ["css-modules", "styled-components", "tailwind"]}}, "required": []},
         "function": _react_component},
        {"name": "color_palette", "description": "Generate a color scheme (complementary, analogous, triadic, monochromatic)",
         "parameters": {"type": "object", "properties": {"base_color": {"type": "string"}, "mode": {"type": "string", "enum": ["complementary", "analogous", "triadic", "monochromatic"]}, "count": {"type": "integer"}}, "required": []},
         "function": _color_palette},
        {"name": "css_animation", "description": "Generate CSS keyframe animation code",
         "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "type": {"type": "string", "enum": ["fade", "slide-up", "slide-down", "scale", "rotate", "bounce", "shake", "pulse"]}, "duration": {"type": "string"}, "easing": {"type": "string"}, "iterations": {"type": "string"}}, "required": []},
         "function": _css_animation},
        {"name": "dark_mode_theme", "description": "Generate CSS custom properties for light/dark theme toggle",
         "parameters": {"type": "object", "properties": {"primary": {"type": "string"}, "background_light": {"type": "string"}, "background_dark": {"type": "string"}, "text_light": {"type": "string"}, "text_dark": {"type": "string"}}, "required": []},
         "function": _dark_mode_theme},
        {"name": "meta_tags", "description": "Generate Open Graph, Twitter Cards, and JSON-LD structured data",
         "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "description": {"type": "string"}, "url": {"type": "string"}, "image": {"type": "string"}, "type": {"type": "string"}, "twitter_handle": {"type": "string"}}, "required": []},
         "function": _meta_tags},
        {"name": "gradient_gen", "description": "Generate CSS gradient (linear, radial, or conic)",
         "parameters": {"type": "object", "properties": {"type": {"type": "string", "enum": ["linear", "radial", "conic"]}, "colors": {"type": "array", "items": {"type": "string"}}, "angle": {"type": "integer"}, "shape": {"type": "string"}}, "required": []},
         "function": _gradient_gen},
        {"name": "accessibility_check", "description": "Run WCAG accessibility audit on an HTML string",
         "parameters": {"type": "object", "properties": {"html_content": {"type": "string"}}, "required": ["html_content"]},
         "function": _accessibility_check},
        {"name": "tailwind_component", "description": "Generate a Tailwind CSS component (card, navbar, hero, form, button)",
         "parameters": {"type": "object", "properties": {"type": {"type": "string", "enum": ["card", "navbar", "hero", "form", "button"]}, "variant": {"type": "string"}, "dark_mode": {"type": "boolean"}}, "required": []},
         "function": _tailwind_component},
    ]


def get_tools():
    return adapt_tools(_raw_tools())
