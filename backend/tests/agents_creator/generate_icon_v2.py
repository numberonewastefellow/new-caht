"""
Generate professional agent icons using real SVG icons from Iconify API.

Searches 200k+ icons across 100+ sets (Material Design, Fluent, Carbon, etc.),
downloads SVGs, renders them on themed backgrounds, and uploads to VirtualAI.

Dependencies:
    pip install Pillow svglib reportlab requests

Usage:
    python generate_icon_v2.py --preview            # Preview all agents
    python generate_icon_v2.py --all                # Generate & upload for all agents
    python generate_icon_v2.py --id 48              # Single agent
    python generate_icon_v2.py --preview --style flat  # Use flat colored icons
    python generate_icon_v2.py --search "cybersecurity" # Test icon search
"""

import argparse
import hashlib
import io
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import tempfile

try:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM
    HAS_SVG_RENDERER = True
except ImportError:
    HAS_SVG_RENDERER = False
    print("[WARN] svglib/reportlab not installed. Install with: pip install svglib reportlab")
    print("       Falling back to text-based icons for SVG rendering.\n")

from config import api, CONFIG, resolve_api_key

# ── Iconify API ──────────────────────────────────────────────────────────────

ICONIFY_API = "https://api.iconify.design"

# Preferred icon sets (ordered by quality/consistency for avatars)
PREFERRED_SETS = [
    "mdi",              # Material Design Icons — large, consistent, filled
    "fluent",           # Microsoft Fluent — modern, professional
    "carbon",           # IBM Carbon — clean, enterprise
    "ph-bold",          # Phosphor Bold — good weight for small sizes
    "tabler",           # Tabler — clean line icons
    "lucide",           # Lucide — clean, modern
    "ri",               # Remix Icon — good filled variants
    "ic",               # Google Material Symbols
    "heroicons",        # Heroicons — Tailwind ecosystem
    "mingcute",         # MingCute — modern, polished
]

# Flat/colored icon sets (for --style flat)
FLAT_SETS = [
    "flat-color-icons",
    "noto",
    "twemoji",
    "fluent-emoji-flat",
    "emojione-v1",
    "fxemoji",
    "openmoji",
]

# ── Keyword Extraction ───────────────────────────────────────────────────────

# Map domain terms to better search queries
DOMAIN_KEYWORDS = {
    # Cybersecurity
    "cybersecurity": ["shield-lock", "security shield", "cyber security"],
    "soc triage": ["shield alert", "security monitoring", "radar"],
    "soc analyst": ["shield alert", "security monitoring", "radar"],
    "triage": ["filter", "priority", "sort"],
    "forensics": ["magnifying glass", "investigate", "fingerprint"],
    "incident": ["alert", "warning", "siren"],
    "malware": ["bug", "virus", "malware"],
    "threat": ["target", "crosshair", "threat"],
    "vulnerability": ["shield off", "shield broken"],
    "firewall": ["firewall", "shield", "wall"],
    "penetration": ["lock open", "break", "hack"],
    "encryption": ["lock", "key", "encrypt"],
    "network": ["network", "lan", "ethernet"],

    # Medical
    "medical": ["stethoscope", "medical", "health"],
    "diagnosis": ["clipboard check", "diagnosis", "medical report"],
    "patient": ["user heart", "patient", "person"],
    "surgery": ["scalpel", "surgery", "cut"],
    "pharmacy": ["pill", "medicine", "capsule"],
    "radiology": ["scan", "x-ray", "radiology"],
    "cardiology": ["heart pulse", "heartbeat", "cardiology"],
    "neurology": ["brain", "neurology", "neuroscience"],
    "pathology": ["microscope", "lab", "test tube"],
    "emergency": ["ambulance", "emergency", "siren"],
    "nurse": ["nurse", "medical team", "care"],

    # Finance
    "finance": ["chart", "trending up", "money"],
    "stock": ["chart line", "trending", "candlestick"],
    "banking": ["bank", "building columns", "vault"],
    "insurance": ["shield check", "umbrella", "protection"],
    "investment": ["chart up", "growth", "invest"],
    "tax": ["receipt", "calculator", "tax"],
    "audit": ["clipboard list", "audit", "check list"],
    "loan": ["hand coins", "loan", "credit"],
    "crypto": ["bitcoin", "currency", "blockchain"],

    # Legal
    "legal": ["gavel", "scales", "law"],
    "court": ["courthouse", "gavel", "justice"],
    "police": ["badge", "shield star", "police"],
    "crime": ["alert triangle", "crime", "detective"],
    "lawyer": ["briefcase", "scales justice", "attorney"],
    "compliance": ["clipboard check", "verified", "compliance"],

    # Technology
    "software": ["code", "terminal", "developer"],
    "database": ["database", "server", "storage"],
    "cloud": ["cloud", "cloud computing", "server"],
    "devops": ["infinity", "pipeline", "deploy"],
    "api": ["webhook", "plug", "api"],
    "ai": ["brain circuit", "robot", "artificial intelligence"],
    "machine learning": ["brain", "neural", "algorithm"],
    "data": ["chart bar", "analytics", "data"],

    # Government
    "government": ["building", "landmark", "capitol"],
    "election": ["vote", "ballot", "check vote"],
    "administration": ["building office", "clipboard", "admin"],
    "panchayat": ["village", "house", "community"],
    "municipality": ["city", "building", "office"],
    "irrigation": ["droplet", "water", "sprinkler"],
    "disaster": ["alert circle", "flame", "flood"],
    "education": ["graduation cap", "school", "book"],
    "welfare": ["hand heart", "charity", "help"],
    "transport": ["truck", "bus", "car"],
    "environment": ["leaf", "tree", "nature"],
    "agriculture": ["wheat", "plant", "tractor"],

    # Business
    "marketing": ["megaphone", "bullhorn", "campaign"],
    "sales": ["handshake", "deal", "chart trending up"],
    "hr": ["users", "people", "team"],
    "project": ["kanban", "clipboard", "task"],
    "strategy": ["chess", "target", "compass"],
    "startup": ["rocket", "launch", "startup"],

    # Creative
    "writing": ["pen", "edit", "pencil"],
    "design": ["palette", "brush", "design"],
    "photography": ["camera", "image", "photo"],
    "music": ["music note", "headphones", "audio"],
    "video": ["video", "film", "camera"],
    "gaming": ["gamepad", "controller", "game"],

    # Science
    "science": ["flask", "atom", "experiment"],
    "research": ["microscope", "search", "beaker"],
    "chemistry": ["flask round", "chemistry", "molecule"],
    "physics": ["atom", "magnet", "energy"],
    "biology": ["dna", "bacteria", "cell"],
    "space": ["rocket", "planet", "satellite"],

    # Real Estate
    "real estate": ["home", "building", "house"],
    "property": ["house", "key", "door"],
    "construction": ["hard hat", "crane", "building"],
    "interior": ["lamp", "sofa", "paint roller"],

    # Entertainment
    "entertainment": ["film", "theater", "popcorn"],
    "sports": ["trophy", "medal", "football"],
    "travel": ["plane", "map", "globe"],
    "food": ["chef hat", "restaurant", "utensils"],

    # Insurance/Claims
    "claims": ["clipboard check", "document", "file check"],
    "underwriting": ["file search", "magnifying", "assessment"],
    "risk": ["alert triangle", "gauge", "warning"],

    # M&A / Due Diligence
    "due diligence": ["search check", "audit", "verify"],
    "merger": ["git merge", "combine", "handshake"],
    "acquisition": ["shopping bag", "cart", "buy"],
    "valuation": ["chart", "calculator", "money"],

    # Drug Development
    "drug": ["pill", "capsule", "medicine"],
    "clinical trial": ["clipboard", "test tube", "experiment"],
    "pharmaceutical": ["pill", "flask", "laboratory"],
    "fda": ["badge check", "certified", "approved"],

    # Engineering
    "engineering": ["wrench", "cog", "settings"],
    "mechanical": ["cog", "gear", "engine"],
    "electrical": ["zap", "bolt", "circuit"],
    "structural": ["building", "layers", "foundation"],
    "failure": ["alert octagon", "x circle", "broken"],
    "analysis": ["chart", "bar chart", "analytics"],
}

# Words to skip when extracting keywords
SKIP_WORDS = {
    "a", "an", "the", "and", "or", "of", "for", "in", "to", "with",
    "by", "on", "at", "is", "as", "it", "its", "be", "was", "were",
    "agent", "assistant", "manager", "specialist", "expert", "advisor",
    "consultant", "analyst", "coordinator", "officer", "supervisor",
    "wrapper", "panel", "workflow", "bot", "helper", "guide",
    "&", "-", "—", "/",
}


def extract_search_queries(name: str, labels: list[str]) -> list[str]:
    """Extract ranked search queries from agent name and labels.

    Returns a list of search strings, best first.
    """
    queries = []
    name_lower = name.lower()
    all_text = name_lower + " " + " ".join(l.lower() for l in labels)
    # Tokenize for word-boundary matching
    all_words = set(re.split(r'[\s&/\-—]+', all_text))

    # 1. Check domain keyword map — prioritize NAME matches over label matches
    #    Use word-boundary matching for single words to avoid substring false positives
    name_words = set(re.split(r'[\s&/\-—]+', name_lower))
    multi_word = {k: v for k, v in DOMAIN_KEYWORDS.items() if " " in k}
    single_word = {k: v for k, v in DOMAIN_KEYWORDS.items() if " " not in k}

    # Name-specific matches first (higher priority)
    for term, search_terms in multi_word.items():
        if term in name_lower:
            queries.extend(search_terms)
    for term, search_terms in single_word.items():
        if term in name_words:
            queries.extend(search_terms)

    # Then label-specific matches
    label_text = " ".join(l.lower() for l in labels)
    label_words = set(re.split(r'[\s&/\-—]+', label_text))
    for term, search_terms in multi_word.items():
        if term in label_text and term not in name_lower:
            queries.extend(search_terms)
    for term, search_terms in single_word.items():
        if term in label_words and term not in name_words:
            queries.extend(search_terms)

    # 2. Use labels as search terms
    for label in labels:
        label_clean = label.strip().lower()
        if label_clean and label_clean not in SKIP_WORDS:
            queries.append(label_clean)

    # 3. Extract meaningful words from name
    words = re.split(r'[\s&/\-—]+', name_lower)
    meaningful = [w for w in words if w and w not in SKIP_WORDS and len(w) > 2]
    for word in meaningful:
        if word not in [q.lower() for q in queries]:
            queries.append(word)

    # 4. Try bigrams from name
    if len(meaningful) >= 2:
        for i in range(len(meaningful) - 1):
            bigram = f"{meaningful[i]} {meaningful[i+1]}"
            queries.insert(len(queries) // 2, bigram)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for q in queries:
        if q.lower() not in seen:
            seen.add(q.lower())
            unique.append(q)

    return unique[:15]  # Limit to top 15 queries


# ── Iconify Search & Download ────────────────────────────────────────────────

# Local cache directory
CACHE_DIR = Path(__file__).parent / "icon_cache"


def search_iconify(query: str, limit: int = 32, prefixes: str | None = None) -> dict:
    """Search Iconify API for icons matching query."""
    params = {"query": query, "limit": limit}
    if prefixes:
        params["prefixes"] = prefixes

    try:
        resp = requests.get(f"{ICONIFY_API}/search", params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except requests.RequestException as e:
        print(f"  [WARN] Iconify search failed: {e}")

    return {"icons": [], "total": 0}


def score_icon(icon_name: str, query: str) -> int:
    """Score an icon based on preference (higher = better)."""
    prefix, name = icon_name.split(":", 1) if ":" in icon_name else ("", icon_name)
    score = 0

    # Prefer specific icon sets
    for i, pref in enumerate(PREFERRED_SETS):
        if prefix == pref:
            score += (len(PREFERRED_SETS) - i) * 10
            break

    # Prefer filled variants
    if "filled" in name or "solid" in name or "-fill" in name:
        score += 15
    if "outline" in name or "twotone" in name or "-line" in name:
        score -= 5

    # Prefer larger viewport icons (24px, 32px, 48px) over tiny (12, 16)
    import re as _re
    size_match = _re.search(r"-(\d+)-", name)
    if size_match:
        icon_size = int(size_match.group(1))
        if icon_size >= 48:
            score += 25
        elif icon_size >= 32:
            score += 20
        elif icon_size >= 24:
            score += 15
        elif icon_size >= 20:
            score += 10
        elif icon_size <= 16:
            score -= 10  # Penalize tiny viewports

    # Prefer shorter names (more generic/recognizable)
    # But don't penalize size suffixes
    clean_name = _re.sub(r"-\d+-(filled|regular)", "", name)
    score -= len(clean_name) // 5

    # Exact query match bonus
    query_words = query.lower().split()
    name_words = name.lower().replace("-", " ").split()
    matching = sum(1 for w in query_words if w in name_words)
    score += matching * 20

    return score


def find_best_icon(
    queries: list[str],
    style: str = "monochrome",
    max_searches: int = 5,
) -> str | None:
    """Search Iconify for the best icon matching the queries.

    Returns icon identifier like "mdi:shield-lock" or None.
    """
    target_sets = ",".join(FLAT_SETS) if style == "flat" else ",".join(PREFERRED_SETS)
    all_candidates = []

    for query in queries[:max_searches]:
        # Search in preferred sets first
        result = search_iconify(query, limit=32, prefixes=target_sets)
        for icon in result.get("icons", []):
            all_candidates.append((icon, score_icon(icon, query)))

        # If we found good results, don't need more searches
        if len(all_candidates) >= 5:
            break

        # Brief delay to be nice to the API
        time.sleep(0.1)

    if not all_candidates:
        # Broader search without set filter
        for query in queries[:3]:
            result = search_iconify(query, limit=32)
            for icon in result.get("icons", []):
                all_candidates.append((icon, score_icon(icon, query)))
            if all_candidates:
                break
            time.sleep(0.1)

    if not all_candidates:
        return None

    # Sort by score descending
    all_candidates.sort(key=lambda x: x[1], reverse=True)
    return all_candidates[0][0]


def download_svg(icon_id: str, color: str | None = None, size: int = 128) -> str | None:
    """Download SVG from Iconify. Returns SVG string or None."""
    prefix, name = icon_id.split(":", 1) if ":" in icon_id else ("", icon_id)
    if not prefix or not name:
        return None

    # Check cache first
    cache_key = f"{prefix}_{name}_{color or 'default'}_{size}"
    cache_file = CACHE_DIR / f"{cache_key}.svg"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")

    # Build URL with params
    url = f"{ICONIFY_API}/{prefix}/{name}.svg"
    params = {"height": str(size)}
    if color:
        # Use # directly — requests will URL-encode it properly for the request,
        # and Iconify will embed the actual color value in the SVG
        params["color"] = f"#{color.lstrip('#')}"

    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200 and resp.text.strip().startswith("<svg"):
            # Cache it
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(resp.text, encoding="utf-8")
            return resp.text
    except requests.RequestException as e:
        print(f"  [WARN] SVG download failed for {icon_id}: {e}")

    return None


# ── SVG to PNG Rendering ─────────────────────────────────────────────────────


def svg_to_rgba(svg_content: str, width: int = 128, height: int = 128,
                target_color: tuple[int, int, int] = (255, 255, 255)) -> Image.Image | None:
    """Convert SVG string to RGBA Pillow Image with transparency.

    svglib renders RGB only (no alpha). So we:
    1. Render the SVG as black-on-white (default colors)
    2. Use pixel darkness as opacity (dark = opaque, white = transparent)
    3. Recolor to target_color with proper alpha

    Returns a Pillow RGBA Image or None.
    """
    if not HAS_SVG_RENDERER:
        return None

    # Strip any color overrides — we want black icon on white background
    import re as _re
    clean_svg = _re.sub(r'fill="[^"]*"', 'fill="#000000"', svg_content)

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False, mode="w",
                                          encoding="utf-8") as tmp:
            tmp.write(clean_svg)
            tmp_path = tmp.name

        drawing = svg2rlg(tmp_path)
        if not drawing:
            return None

        # Scale drawing to target size
        orig_w = drawing.width or width
        orig_h = drawing.height or height
        scale = min(width / orig_w, height / orig_h)
        drawing.width = width
        drawing.height = height
        drawing.scale(scale, scale)

        png_bytes = renderPM.drawToString(drawing, fmt="PNG", dpi=72)
        rgb_img = Image.open(io.BytesIO(png_bytes)).convert("RGB")

        # Create alpha from luminance: dark pixels → opaque, white → transparent
        # Invert grayscale: 0=white(transparent), 255=black(opaque)
        gray = rgb_img.convert("L")
        from PIL import ImageOps
        alpha = ImageOps.invert(gray)

        # Create solid-color image with the alpha mask
        colored = Image.new("RGBA", rgb_img.size, target_color + (255,))
        colored.putalpha(alpha)

        return colored
    except Exception as e:
        print(f"  [WARN] SVG→RGBA conversion failed: {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ── Color Helpers ─────────────────────────────────────────────────────────────

# Department color palette — VIBRANT gradient pairs (top_color, bottom_color)
DEPARTMENT_COLORS = {
    # Government & Admin
    "police & law": ("#1E88E5", "#0D47A1"),           # Bright blue gradient
    "district administration": ("#AB47BC", "#6A1B9A"), # Vivid purple
    "village & panchayat": ("#66BB6A", "#2E7D32"),     # Fresh green
    "municipal services": ("#26C6DA", "#00838F"),      # Cyan
    "government": ("#5C6BC0", "#283593"),              # Indigo
    "legal": ("#607D8B", "#37474F"),                   # Blue grey (refined)
    "disaster management": ("#FF7043", "#D84315"),     # Vivid orange
    "water & irrigation": ("#29B6F6", "#0277BD"),      # Sky blue

    # Social
    "healthcare": ("#EF5350", "#C62828"),              # Vivid red
    "education": ("#42A5F5", "#1565C0"),               # Bright blue
    "competitive exams": ("#1E88E5", "#0D47A1"),       # Deep blue
    "sports & youth": ("#FFA726", "#E65100"),           # Amber-orange
    "welfare": ("#66BB6A", "#2E7D32"),                 # Green

    # Infrastructure
    "infrastructure": ("#78909C", "#455A64"),          # Steel
    "transport": ("#5C6BC0", "#303F9F"),               # Indigo-blue
    "labour & industry": ("#FF7043", "#BF360C"),       # Deep orange
    "permits & licenses": ("#EC407A", "#AD1457"),      # Pink
    "environment": ("#4DB6AC", "#00695C"),             # Teal

    # Religious
    "religious affairs": ("#FFB74D", "#E65100"),        # Warm amber

    # Finance
    "finance & tax": ("#5C6BC0", "#1A237E"),           # Indigo
    "stock market": ("#4CAF50", "#1B5E20"),            # Rich green
    "investment": ("#66BB6A", "#388E3C"),              # Green
    "banking & loans": ("#42A5F5", "#0D47A1"),         # Blue
    "insurance": ("#CE93D8", "#7B1FA2"),               # Bright purple
    "personal finance": ("#26C6DA", "#00695C"),        # Teal-cyan
    "crypto & forex": ("#FFD54F", "#F9A825"),          # Gold
    "startups & business": ("#BA68C8", "#6A1B9A"),     # Purple

    # Real Estate
    "real estate": ("#FF8A65", "#BF360C"),             # Warm terracotta
    "interior & renovation": ("#F06292", "#AD1457"),   # Hot pink

    # Entertainment
    "entertainment": ("#F06292", "#C2185B"),            # Rose
    "creative writing": ("#A1887F", "#4E342E"),        # Warm cocoa
    "gaming": ("#7986CB", "#283593"),                  # Indigo
    "photography & visual arts": ("#90A4AE", "#455A64"), # Cool grey

    # Science & Tech
    "science": ("#4FC3F7", "#0277BD"),                 # Light blue
    "ai & robotics": ("#7C4DFF", "#311B92"),           # Electric purple
    "technology": ("#7986CB", "#283593"),              # Indigo
    "web & mobile dev": ("#42A5F5", "#1565C0"),        # Blue
    "networking & sysadmin": ("#4DB6AC", "#00695C"),   # Teal
    "cybersecurity": ("#EF5350", "#B71C1C"),           # Bold red
    "cloud & devops": ("#4FC3F7", "#0277BD"),          # Sky blue

    # Marketing
    "digital marketing": ("#42A5F5", "#1565C0"),       # Blue
    "social media": ("#F06292", "#C2185B"),            # Pink
    "content creation": ("#EF5350", "#C62828"),        # Red
    "linkedin": ("#29B6F6", "#0277BD"),                # LinkedIn blue
    "twitter & instagram": ("#F06292", "#880E4F"),     # Magenta-pink

    # Workflow (for WF agents)
    "workflow": ("#7986CB", "#3949AB"),                # Indigo
    "discussion": ("#4FC3F7", "#0277BD"),              # Sky blue
    "engineering": ("#78909C", "#37474F"),             # Steel grey
}


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def lighten_color(hex_color: str, factor: float = 0.3) -> str:
    """Lighten a hex color by mixing with white."""
    r, g, b = hex_to_rgb(hex_color)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


def hsl_to_hex(h: int, s: float, l: float) -> str:
    """Convert HSL to hex color."""
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    if h < 60: r, g, b = c, x, 0
    elif h < 120: r, g, b = x, c, 0
    elif h < 180: r, g, b = 0, c, x
    elif h < 240: r, g, b = 0, x, c
    elif h < 300: r, g, b = x, 0, c
    else: r, g, b = c, 0, x
    r, g, b = int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)
    return f"#{r:02x}{g:02x}{b:02x}"


def get_color_for_agent(name: str, labels: list[str]) -> tuple[str, str]:
    """Get (background, accent) color based on agent labels."""
    for label in labels:
        key = label.lower()
        if key in DEPARTMENT_COLORS:
            return DEPARTMENT_COLORS[key]

    h = int(hashlib.md5(name.encode()).hexdigest()[:6], 16)
    hue = h % 360
    # Vibrant: lighter top, darker bottom
    return (hsl_to_hex(hue, 0.75, 0.55), hsl_to_hex(hue, 0.8, 0.30))


# ── Icon Rendering ───────────────────────────────────────────────────────────

FONT_BOLD_PATH = "C:/Windows/Fonts/segoeuib.ttf"


def generate_icon_with_svg(
    name: str,
    labels: list[str],
    icon_id: str | None = None,
    size: int = 256,
    style: str = "monochrome",
) -> tuple[bytes, str | None]:
    """Generate a professional icon with a real SVG icon from Iconify.

    Returns (png_bytes, icon_id_used).
    """
    bg_color, accent_color = get_color_for_agent(name, labels)

    # Search for icon if not provided
    if not icon_id:
        queries = extract_search_queries(name, labels)
        print(f"  Search queries: {queries[:5]}")
        icon_id = find_best_icon(queries, style=style)

    if icon_id:
        print(f"  Icon found: {icon_id}")
    else:
        print(f"  No icon found, using text fallback")
        return _generate_text_icon(name, labels, size), None

    # Download SVG (always without color — we recolor ourselves for proper alpha)
    icon_size = int(size * 0.55)  # Icon takes ~55% of the canvas
    svg = download_svg(icon_id, size=icon_size)

    if not svg:
        print(f"  SVG download failed, using text fallback")
        return _generate_text_icon(name, labels, size), None

    # Convert SVG to RGBA image with proper transparency
    if style == "flat":
        # For flat: use accent color
        r, g, b = hex_to_rgb(accent_color)
        icon_img = svg_to_rgba(svg, icon_size, icon_size, target_color=(r, g, b))
    else:
        # For monochrome: white icon
        icon_img = svg_to_rgba(svg, icon_size, icon_size, target_color=(255, 255, 255))

    if not icon_img:
        print(f"  SVG→PNG failed, using text fallback")
        return _generate_text_icon(name, labels, size), None

    if style == "flat":
        # For flat style: transparent background, just the colored icon
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        x = (size - icon_img.width) // 2
        y = (size - icon_img.height) // 2
        canvas.paste(icon_img, (x, y), icon_img)
    else:
        # Monochrome style: colored background + white icon
        canvas = _render_themed_background(size, bg_color, accent_color)
        x = (size - icon_img.width) // 2
        y = (size - icon_img.height) // 2 - size // 20  # Slight upward offset
        canvas.paste(icon_img, (x, y), icon_img)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue(), icon_id


def _render_themed_background(size: int, bg_color: str, accent_color: str) -> Image.Image:
    """Render a vibrant gradient background with rounded corners."""
    # bg_color = top color (lighter), accent_color = bottom color (darker)
    top_r, top_g, top_b = hex_to_rgb(bg_color)
    bot_r, bot_g, bot_b = hex_to_rgb(accent_color)

    margin = 4
    radius = size // 6

    # Create gradient image
    gradient = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)

    # Draw vertical gradient line by line
    for y in range(margin, size - margin):
        t = (y - margin) / (size - 2 * margin)  # 0.0 at top → 1.0 at bottom
        r = int(top_r + (bot_r - top_r) * t)
        g = int(top_g + (bot_g - top_g) * t)
        b = int(top_b + (bot_b - top_b) * t)
        draw.line([(margin, y), (size - margin, y)], fill=(r, g, b, 255))

    # Apply rounded corner mask
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius,
        fill=255,
    )
    gradient.putalpha(mask)

    # Add subtle shine overlay at top
    shine = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shine_draw = ImageDraw.Draw(shine)
    for y in range(margin, size // 3):
        alpha = int(50 * (1 - (y - margin) / (size // 3 - margin)))
        shine_draw.line([(margin, y), (size - margin, y)], fill=(255, 255, 255, alpha))
    gradient = Image.alpha_composite(gradient, shine)
    gradient.putalpha(mask)

    return gradient


def _generate_text_icon(name: str, labels: list[str], size: int = 256) -> bytes:
    """Fallback: generate text-based icon (same as v1)."""
    bg_color, accent_color = get_color_for_agent(name, labels)

    # Get initials
    skip = {"&", "and", "the", "of", "for", "in", "a", "an", "to",
            "agent", "assistant", "manager", "specialist", "expert",
            "wrapper", "panel", "workflow"}
    words = name.split()
    meaningful = [w for w in words if w.lower() not in skip]
    if len(meaningful) >= 2:
        initials = (meaningful[0][0] + meaningful[1][0]).upper()
    elif meaningful:
        initials = meaningful[0][:2].upper()
    else:
        initials = name[:2].upper()

    img = _render_themed_background(size, bg_color, accent_color)
    draw = ImageDraw.Draw(img)

    # Draw initials
    try:
        font = ImageFont.truetype(FONT_BOLD_PATH, size // 3)
    except (OSError, IOError):
        font = ImageFont.load_default()

    stripe_h = size // 10
    text_area_height = size - stripe_h - 8
    bbox = draw.textbbox((0, 0), initials, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (size - text_w) // 2
    text_y = (text_area_height - text_h) // 2

    draw.text((text_x + 1, text_y + 1), initials, fill=(0, 0, 0, 80), font=font)
    draw.text((text_x, text_y), initials, fill="white", font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── Upload & API ─────────────────────────────────────────────────────────────


def upload_image(image_bytes: bytes, filename: str) -> str | None:
    """Upload image to VirtualAI and return file_id."""
    url = f"{CONFIG['base_url']}/api/admin/agent/upload-image"
    auth_headers = {"Authorization": f"Bearer {resolve_api_key()}"}
    files = {"file": (filename, io.BytesIO(image_bytes), "image/png")}

    resp = requests.post(url, headers=auth_headers, files=files, timeout=30)
    if resp.status_code == 200:
        return resp.json().get("file_id")
    else:
        print(f"  [ERR] Upload failed: {resp.status_code} — {resp.text[:200]}")
        return None


def update_agent_image(agent_id: int, file_id: str) -> bool:
    """Update agent with uploaded image."""
    get_resp = api("GET", f"agent/{agent_id}")
    if get_resp.status_code != 200:
        print(f"  [ERR] GET agent {agent_id}: {get_resp.status_code}")
        return False

    agent = get_resp.json()
    update_data = {
        "name": agent["name"],
        "description": agent.get("description", ""),
        "system_prompt": agent.get("system_prompt", ""),
        "task_prompt": agent.get("task_prompt", ""),
        "num_chunks": agent.get("num_chunks", 10.0),
        "is_public": agent.get("is_public", True),
        "recency_bias": agent.get("recency_bias", "base_decay"),
        "llm_filter_extraction": agent.get("llm_filter_extraction", False),
        "llm_relevance_filter": agent.get("llm_relevance_filter", False),
        "replace_base_system_prompt": agent.get("replace_base_system_prompt", True),
        "datetime_aware": agent.get("datetime_aware", True),
        "document_set_ids": [ds["id"] for ds in agent.get("document_sets", [])],
        "tool_ids": [t["id"] for t in agent.get("tools", [])],
        "starter_messages": agent.get("starter_messages", []),
        "users": agent.get("users", []),
        "groups": agent.get("groups", []),
        "label_ids": [lbl["id"] for lbl in agent.get("labels", [])],
        "knowledge_file_ids": [],
        "hierarchy_node_ids": [],
        "document_ids": [],
        "uploaded_image_id": file_id,
        "remove_image": False,
    }

    resp = api("PATCH", f"agent/{agent_id}", update_data)
    if resp.status_code != 200:
        print(f"  [ERR] PATCH {resp.status_code}: {resp.text[:300]}")
    return resp.status_code == 200


def get_all_agents() -> list[dict]:
    """Fetch all agents."""
    resp = api("GET", "agent")
    if resp.status_code != 200:
        print(f"Failed to list agents: {resp.status_code}")
        return []
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "description": p.get("description", ""),
            "labels": [lbl["name"] for lbl in p.get("labels", [])],
            "uploaded_image_id": p.get("uploaded_image_id"),
        }
        for p in resp.json()
    ]


# ── Processing ───────────────────────────────────────────────────────────────


def process_agent(
    agent: dict,
    preview_dir: str | None = None,
    upload: bool = True,
    style: str = "monochrome",
    force_icon: str | None = None,
) -> bool:
    """Generate icon and optionally upload for one agent."""
    name = agent["name"]
    labels = agent.get("labels", [])
    agent_id = agent.get("id")

    print(f"\n{'='*60}")
    print(f"  Agent: {name} (ID={agent_id})")
    print(f"  Labels: {', '.join(labels)}")

    icon_bytes, icon_used = generate_icon_with_svg(
        name, labels, icon_id=force_icon, style=style
    )
    print(f"  Icon generated: {len(icon_bytes)} bytes")
    if icon_used:
        print(f"  Icon source: {icon_used}")

    if preview_dir:
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)[:50]
        preview_path = os.path.join(preview_dir, f"{agent_id}_{safe_name}.png")
        with open(preview_path, "wb") as f:
            f.write(icon_bytes)
        print(f"  Preview saved: {preview_path}")

    if not upload:
        return True

    file_id = upload_image(icon_bytes, f"agent_{agent_id}_{name[:20]}.png")
    if not file_id:
        print(f"  [FAIL] Image upload failed")
        return False
    print(f"  Uploaded: file_id={file_id}")

    if update_agent_image(agent_id, file_id):
        print(f"  [OK] Image set for {name}")
        return True
    else:
        print(f"  [FAIL] Could not update agent {agent_id}")
        return False


def cmd_search(query: str, style: str = "monochrome"):
    """Test the icon search for a given query."""
    print(f"\nSearching for: '{query}' (style={style})\n")

    target_sets = FLAT_SETS if style == "flat" else PREFERRED_SETS
    result = search_iconify(query, limit=32, prefixes=",".join(target_sets))
    icons = result.get("icons", [])

    if not icons:
        # Try broader search
        result = search_iconify(query, limit=32)
        icons = result.get("icons", [])

    print(f"Found {result.get('total', 0)} total, showing top {len(icons)}:\n")

    scored = [(icon, score_icon(icon, query)) for icon in icons]
    scored.sort(key=lambda x: x[1], reverse=True)

    for i, (icon, score) in enumerate(scored[:20]):
        prefix, name = icon.split(":", 1) if ":" in icon else ("?", icon)
        print(f"  {i+1:2d}. {icon:<45s}  (score={score:3d}, set={prefix})")

    if scored:
        best = scored[0][0]
        print(f"\n  Best match: {best}")
        print(f"  SVG URL: {ICONIFY_API}/{best.replace(':', '/')}.svg")


def main():
    parser = argparse.ArgumentParser(description="Generate agent icons using Iconify API")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preview", action="store_true", help="Generate preview images only")
    group.add_argument("--all", action="store_true", help="Generate & upload for all agents")
    group.add_argument("--id", type=int, help="Process a specific agent ID")
    group.add_argument("--search", type=str, help="Test icon search for a query")
    group.add_argument("--test", action="store_true", help="Test with one agent")

    parser.add_argument("--style", choices=["monochrome", "flat"], default="monochrome",
                        help="Icon style: monochrome (white on color) or flat (colored icon)")
    parser.add_argument("--icon", type=str, help="Force a specific icon ID (e.g. mdi:shield-lock)")
    parser.add_argument("--preview-dir", type=str, default="icons_v2_preview",
                        help="Directory for preview images")

    args = parser.parse_args()

    if args.search:
        cmd_search(args.search, style=args.style)
        return

    resolve_api_key()

    if args.test:
        agent = {
            "id": 48,
            "name": "Municipal Property Tax & Revenue Manager",
            "labels": ["Municipal Services"],
        }
        print("=== TEST: Generating icon ===")
        os.makedirs(args.preview_dir, exist_ok=True)
        process_agent(agent, preview_dir=args.preview_dir, upload=False,
                      style=args.style, force_icon=args.icon)
        print(f"\n=== Check: {args.preview_dir}/ ===")
        return

    if args.preview:
        agents = get_all_agents()
        custom = [p for p in agents if p["labels"]]
        os.makedirs(args.preview_dir, exist_ok=True)
        print(f"Generating icons for {len(custom)} agents (style={args.style})...\n")
        for agent in custom:
            process_agent(agent, preview_dir=args.preview_dir, upload=False,
                          style=args.style, force_icon=args.icon)
        print(f"\nDone! Icons saved to: {args.preview_dir}/")
        return

    if args.id:
        agents = get_all_agents()
        agent = next((p for p in agents if p["id"] == args.id), None)
        if not agent:
            print(f"Agent ID {args.id} not found")
            sys.exit(1)
        process_agent(agent, style=args.style, force_icon=args.icon)
        return

    if args.all:
        agents = get_all_agents()
        custom = [p for p in agents if p["labels"]]
        print(f"Processing {len(custom)} agents (style={args.style})...")
        ok, fail = 0, 0
        for agent in custom:
            if process_agent(agent, style=args.style, force_icon=args.icon):
                ok += 1
            else:
                fail += 1
        print(f"\nDone: {ok} succeeded, {fail} failed")


if __name__ == "__main__":
    main()
