"""
Generate professional avatar icons for VirtualAI agents and upload them.

Usage:
    python generate_icon.py --test              # Test with one agent
    python generate_icon.py --all               # Generate & upload for all agents
    python generate_icon.py --file FILE         # Generate & upload for agents in a JSON file
    python generate_icon.py --id ID             # Generate & upload for a specific agent ID
    python generate_icon.py --preview           # Generate preview images without uploading
"""

import argparse
import hashlib
import io
import json
import math
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from config import api, CONFIG, resolve_api_key

# --- Icon Design Configuration ---

# Color palettes by department/label (warm, professional colors)
DEPARTMENT_COLORS = {
    # Government & Administration
    "police & law": ("#1B3A5C", "#4A90D9"),           # Navy blue
    "district administration": ("#4A0E4E", "#9B59B6"), # Purple
    "village & panchayat": ("#33691E", "#7CB342"),     # Green
    "municipal services": ("#00695C", "#26A69A"),      # Teal
    "government": ("#1A237E", "#3F51B5"),              # Indigo
    "legal": ("#263238", "#546E7A"),                   # Dark grey
    "disaster management": ("#E65100", "#FF9800"),     # Orange
    "water & irrigation": ("#01579B", "#039BE5"),      # Deep blue

    # Social Sector
    "healthcare": ("#C0392B", "#E74C3C"),              # Red
    "education": ("#1565C0", "#42A5F5"),               # Blue
    "competitive exams": ("#0D47A1", "#1E88E5"),       # Deep blue
    "sports & youth": ("#F57F17", "#FFEE58"),          # Yellow
    "welfare": ("#1B5E20", "#43A047"),                 # Green

    # Infrastructure & Industry
    "infrastructure": ("#455A64", "#78909C"),          # Blue grey
    "transport": ("#37474F", "#78909C"),               # Blue-grey
    "labour & industry": ("#BF360C", "#FF7043"),       # Deep orange
    "permits & licenses": ("#880E4F", "#EC407A"),      # Dark pink
    "environment": ("#00695C", "#26A69A"),             # Teal

    # Religious
    "religious affairs": ("#FF6F00", "#FFA726"),        # Amber

    # Finance & Markets
    "finance & tax": ("#1A237E", "#3F51B5"),           # Indigo
    "stock market": ("#1B5E20", "#4CAF50"),            # Green (money)
    "investment": ("#2E7D32", "#66BB6A"),              # Green
    "banking & loans": ("#0D47A1", "#1976D2"),         # Blue
    "insurance": ("#6A1B9A", "#AB47BC"),               # Purple
    "personal finance": ("#00695C", "#26A69A"),        # Teal
    "crypto & forex": ("#F9A825", "#FDD835"),          # Gold/Yellow
    "startups & business": ("#6A1B9A", "#AB47BC"),     # Purple

    # Real Estate
    "real estate": ("#5D4037", "#8D6E63"),             # Brown (earth)
    "interior & renovation": ("#AD1457", "#EC407A"),   # Pink/magenta

    # Entertainment & Creative
    "entertainment": ("#AD1457", "#EC407A"),            # Magenta/Pink
    "creative writing": ("#5D4037", "#A1887F"),        # Warm brown
    "gaming": ("#1565C0", "#64B5F6"),                  # Blue
    "photography & visual arts": ("#37474F", "#78909C"), # Blue grey

    # Science
    "science": ("#0277BD", "#29B6F6"),                 # Light blue
    "ai & robotics": ("#311B92", "#7C4DFF"),           # Deep purple

    # Technology
    "technology": ("#283593", "#7986CB"),              # Indigo
    "web & mobile dev": ("#1565C0", "#42A5F5"),        # Blue
    "networking & sysadmin": ("#00695C", "#26A69A"),   # Teal
    "cybersecurity": ("#C62828", "#EF5350"),            # Red
    "cloud & devops": ("#0277BD", "#29B6F6"),          # Light blue

    # Marketing & Content
    "digital marketing": ("#1565C0", "#42A5F5"),       # Blue
    "social media": ("#E91E63", "#F48FB1"),            # Pink
    "content creation": ("#D32F2F", "#EF5350"),        # Red
    "linkedin": ("#0077B5", "#29B6F6"),                # LinkedIn blue
    "twitter & instagram": ("#C13584", "#F06292"),     # Instagram gradient
}

# Emoji/symbol mapping for agent types
AGENT_SYMBOLS = {
    # Police
    "fir": "\u2696",           # ⚖ scales
    "charge sheet": "\U0001F4CB",  # 📋
    "crime pattern": "\U0001F50D", # 🔍
    "legal section": "\U0001F4D6", # 📖

    # Revenue
    "certificate": "\U0001F4DC",   # 📜
    "land record": "\U0001F5FA",   # 🗺
    "mutation": "\U0001F4DD",      # 📝
    "crop damage": "\U0001F33E",   # 🌾
    "citizen query": "\U0001F4AC", # 💬

    # Collector
    "petition": "\U0001F4E9",      # 📩
    "go reference": "\U0001F4D1",  # 📑
    "report": "\U0001F4CA",        # 📊
    "scheme": "\U0001F3AF",        # 🎯
    "revenue court": "\U0001F3DB", # 🏛

    # Health
    "disease": "\U0001F9EA",       # 🧪
    "drug stock": "\U0001F48A",    # 💊
    "maternal": "\U0001F476",      # 👶
    "health report": "\U0001F4CB", # 📋

    # Disaster
    "flood": "\U0001F30A",         # 🌊
    "drought": "\u2600",           # ☀
    "fire": "\U0001F525",          # 🔥
    "earthquake": "\U0001F3DA",    # 🏚
    "relief camp": "\u26FA",       # ⛺

    # Law & Order
    "riot": "\U0001F6E1",          # 🛡
    "communal": "\U0001F91D",      # 🤝
    "curfew": "\U0001F6A8",        # 🚨

    # Sports & Youth
    "sports": "\U0001F3C6",        # 🏆
    "youth": "\U0001F393",         # 🎓

    # Village
    "panchayat": "\U0001F3D8",     # 🏘
    "mgnrega": "\U0001F6A7",       # 🚧
    "infrastructure": "\U0001F3D7",# 🏗
    "pds": "\U0001F35A",           # 🍚
    "festival": "\U0001F389",      # 🎉
    "sachivalayam": "\U0001F3E2",  # 🏢

    # Education
    "school": "\U0001F3EB",        # 🏫
    "scholarship": "\U0001F4B0",   # 💰

    # Election / RTI / Land
    "election": "\U0001F5F3",      # 🗳
    "rti": "\U0001F4E7",           # 📧
    "land protection": "\U0001F6E1", # 🛡

    # Municipality
    "property tax": "\U0001F3E0",   # 🏠
    "building": "\U0001F3D7",       # 🏗
    "sanitation": "\U0001F9F9",     # 🧹
    "water supply": "\U0001F6B0",   # 🚰
    "trade license": "\U0001F4BC",  # 💼
    "birth": "\U0001F4DD",          # 📝

    # Irrigation
    "dam": "\U0001F4A7",            # 💧
    "canal": "\U0001F30A",          # 🌊
    "micro irrigation": "\U0001F4A6", # 💦
    "water users": "\U0001F91D",    # 🤝

    # Registration
    "registration": "\U0001F4DC",    # 📜
    "stamp duty": "\U0001F4B5",      # 💵
    "encumbrance": "\U0001F50E",     # 🔎
    "sale deed": "\U0001F4C4",       # 📄

    # Sub-departments
    "rto": "\U0001F697",             # 🚗
    "vehicle": "\U0001F697",         # 🚗
    "labour": "\U0001F477",          # 👷
    "factory": "\U0001F3ED",         # 🏭
    "excise": "\U0001F377",          # 🍷
    "mining": "\u26CF",              # ⛏
    "sand": "\u26CF",                # ⛏
    "endowment": "\U0001F6D5",      # 🛕
    "temple": "\U0001F6D5",         # 🛕
    "town planning": "\U0001F4D0",  # 📐
    "zoning": "\U0001F4D0",         # 📐
}

# Font
FONT_PATH = "C:/Windows/Fonts/segoeui.ttf"
FONT_BOLD_PATH = "C:/Windows/Fonts/segoeuib.ttf"
EMOJI_FONT_PATH = "C:/Windows/Fonts/seguiemj.ttf"


def get_color_for_agent(name: str, labels: list[str]) -> tuple[str, str]:
    """Get background and accent color based on agent labels."""
    for label in labels:
        key = label.lower()
        if key in DEPARTMENT_COLORS:
            return DEPARTMENT_COLORS[key]

    # Fallback: generate color from name hash
    h = int(hashlib.md5(name.encode()).hexdigest()[:6], 16)
    hue = h % 360
    # Convert HSL to RGB (dark shade)
    bg = hsl_to_hex(hue, 0.6, 0.25)
    accent = hsl_to_hex(hue, 0.7, 0.55)
    return (bg, accent)


def hsl_to_hex(h: int, s: float, l: float) -> str:
    """Convert HSL to hex color."""
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2

    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x

    r, g, b = int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)
    return f"#{r:02x}{g:02x}{b:02x}"


def get_initials(name: str) -> str:
    """Get 1-2 character initials from agent name."""
    words = name.split()
    # Skip common words
    skip = {"&", "and", "the", "of", "for", "in", "a", "an", "to"}
    meaningful = [w for w in words if w.lower() not in skip]
    if len(meaningful) >= 2:
        return (meaningful[0][0] + meaningful[1][0]).upper()
    elif meaningful:
        return meaningful[0][:2].upper()
    return name[:2].upper()


def get_symbol(name: str) -> str | None:
    """Try to match an emoji symbol for the agent."""
    name_lower = name.lower()
    for key, symbol in AGENT_SYMBOLS.items():
        if key in name_lower:
            return symbol
    return None


def generate_icon(
    name: str,
    labels: list[str],
    size: int = 256,
    style: str = "gradient",
) -> bytes:
    """Generate a professional icon for an agent.

    Returns PNG image as bytes.
    """
    bg_color, accent_color = get_color_for_agent(name, labels)
    initials = get_initials(name)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw rounded rectangle background
    margin = 4
    radius = size // 6
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius,
        fill=bg_color,
    )

    # Draw subtle gradient overlay (lighter at top)
    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    for y in range(margin, size - margin):
        alpha = int(40 * (1 - y / size))  # Subtle white gradient from top
        overlay_draw.line(
            [(margin + radius // 2, y), (size - margin - radius // 2, y)],
            fill=(255, 255, 255, alpha),
        )
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # Draw accent stripe at bottom (simple rectangle)
    stripe_h = size // 8
    stripe_top = size - margin - stripe_h
    stripe_bot = size - margin - 2
    if stripe_bot > stripe_top:
        draw.rectangle(
            [margin + 2, stripe_top, size - margin - 2, stripe_bot],
            fill=accent_color,
        )

    # Draw initials text
    try:
        font_size = size // 3
        font = ImageFont.truetype(FONT_BOLD_PATH, font_size)
    except (OSError, IOError):
        font = ImageFont.load_default()

    # Center the text (in the upper portion, above the stripe)
    text_area_height = size - stripe_h - margin * 2
    bbox = draw.textbbox((0, 0), initials, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (size - text_w) // 2
    text_y = margin + (text_area_height - text_h) // 2 - margin

    # Draw text shadow
    draw.text((text_x + 1, text_y + 1), initials, fill=(0, 0, 0, 80), font=font)
    # Draw text
    draw.text((text_x, text_y), initials, fill="white", font=font)

    # Convert to PNG bytes
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def upload_image(image_bytes: bytes, filename: str) -> str | None:
    """Upload image to VirtualAI and return file_id."""
    import requests

    url = f"{CONFIG['base_url']}/api/admin/persona/upload-image"
    auth_headers = {"Authorization": f"Bearer {resolve_api_key()}"}
    files = {"file": (filename, io.BytesIO(image_bytes), "image/png")}

    # Note: Do NOT set Content-Type header — requests sets multipart boundary automatically
    resp = requests.post(url, headers=auth_headers, files=files, timeout=30)
    if resp.status_code == 200:
        file_id = resp.json().get("file_id")
        return file_id
    else:
        print(f"  [ERR] Upload failed: {resp.status_code} — {resp.text[:200]}")
        return None


def update_persona_image(persona_id: int, file_id: str) -> bool:
    """Update persona with uploaded image by fetching existing data first."""
    # Fetch current persona data
    get_resp = api("GET", f"persona/{persona_id}")
    if get_resp.status_code != 200:
        print(f"  [ERR] GET persona {persona_id}: {get_resp.status_code}")
        return False

    persona = get_resp.json()

    # Build the update payload with all required fields from existing data
    update_data = {
        "name": persona["name"],
        "description": persona.get("description", ""),
        "system_prompt": persona.get("system_prompt", ""),
        "task_prompt": persona.get("task_prompt", ""),
        "num_chunks": persona.get("num_chunks", 10.0),
        "is_public": persona.get("is_public", True),
        "recency_bias": persona.get("recency_bias", "base_decay"),
        "llm_filter_extraction": persona.get("llm_filter_extraction", False),
        "llm_relevance_filter": persona.get("llm_relevance_filter", False),
        "replace_base_system_prompt": persona.get("replace_base_system_prompt", True),
        "datetime_aware": persona.get("datetime_aware", True),
        "document_set_ids": [ds["id"] for ds in persona.get("document_sets", [])],
        "tool_ids": [t["id"] for t in persona.get("tools", [])],
        "starter_messages": persona.get("starter_messages", []),
        "users": persona.get("users", []),
        "groups": persona.get("groups", []),
        "label_ids": [lbl["id"] for lbl in persona.get("labels", [])],
        "user_file_ids": [],
        "hierarchy_node_ids": [],
        "document_ids": [],
        # Image fields
        "uploaded_image_id": file_id,
        "remove_image": False,
    }

    resp = api("PATCH", f"persona/{persona_id}", update_data)
    if resp.status_code != 200:
        print(f"  [ERR] PATCH {resp.status_code}: {resp.text[:300]}")
    return resp.status_code == 200


def get_all_personas() -> list[dict]:
    """Fetch all personas with their labels."""
    resp = api("GET", "persona")
    if resp.status_code != 200:
        print(f"Failed to list personas: {resp.status_code}")
        return []
    personas = resp.json()
    result = []
    for p in personas:
        result.append({
            "id": p["id"],
            "name": p["name"],
            "description": p.get("description", ""),
            "labels": [lbl["name"] for lbl in p.get("labels", [])],
            "uploaded_image_id": p.get("uploaded_image_id"),
        })
    return result


def process_agent(agent: dict, preview_dir: str | None = None, upload: bool = True) -> bool:
    """Generate icon and optionally upload for one agent."""
    name = agent["name"]
    labels = agent.get("labels", [])
    agent_id = agent.get("id")

    print(f"\n  Agent: {name} (ID={agent_id})")
    print(f"  Labels: {', '.join(labels)}")

    # Generate icon
    icon_bytes = generate_icon(name, labels)
    print(f"  Icon generated: {len(icon_bytes)} bytes")

    # Save preview if requested
    if preview_dir:
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)[:50]
        preview_path = os.path.join(preview_dir, f"{agent_id}_{safe_name}.png")
        with open(preview_path, "wb") as f:
            f.write(icon_bytes)
        print(f"  Preview saved: {preview_path}")

    if not upload:
        return True

    # Upload
    file_id = upload_image(icon_bytes, f"agent_{agent_id}_{name[:20]}.png")
    if not file_id:
        print(f"  [FAIL] Image upload failed")
        return False
    print(f"  Uploaded: file_id={file_id}")

    # Update persona
    if update_persona_image(agent_id, file_id):
        print(f"  [OK] Image set for {name}")
        return True
    else:
        print(f"  [FAIL] Could not update persona {agent_id}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate and upload agent icons")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--test", action="store_true", help="Test with one agent (ID=48)")
    group.add_argument("--all", action="store_true", help="Process all custom agents")
    group.add_argument("--file", type=str, help="Process agents from a JSON file")
    group.add_argument("--id", type=int, help="Process a specific agent ID")
    group.add_argument("--preview", action="store_true", help="Generate preview images only (no upload)")
    parser.add_argument("--preview-dir", type=str, default="icons_preview", help="Directory for preview images")

    args = parser.parse_args()
    resolve_api_key()

    if args.preview:
        # Generate previews for all agents
        personas = get_all_personas()
        custom = [p for p in personas if p["labels"]]  # Only agents with labels
        os.makedirs(args.preview_dir, exist_ok=True)
        print(f"Generating preview icons for {len(custom)} agents...")
        for agent in custom:
            process_agent(agent, preview_dir=args.preview_dir, upload=False)
        print(f"\nDone! Preview icons saved to: {args.preview_dir}/")
        return

    if args.test:
        # Test with Municipal Property Tax agent (ID=48)
        agent = {
            "id": 48,
            "name": "Municipal Property Tax & Revenue Manager",
            "labels": ["Municipality", "Revenue", "Property Tax"],
        }
        print("=== TEST: Generating and uploading icon for one agent ===")
        success = process_agent(agent)
        if success:
            print("\n=== SUCCESS! Check the agent in the UI. ===")
        else:
            print("\n=== FAILED. Check errors above. ===")
        return

    if args.id:
        personas = get_all_personas()
        agent = next((p for p in personas if p["id"] == args.id), None)
        if not agent:
            print(f"Agent ID {args.id} not found")
            sys.exit(1)
        process_agent(agent)
        return

    if args.all:
        personas = get_all_personas()
        custom = [p for p in personas if p["labels"]]  # Only agents with labels
        print(f"Processing {len(custom)} agents with labels...")
        ok, fail = 0, 0
        for agent in custom:
            if process_agent(agent):
                ok += 1
            else:
                fail += 1
        print(f"\nDone: {ok} succeeded, {fail} failed")
        return

    if args.file:
        with open(args.file) as f:
            agents = json.load(f)
        # These are JSON definitions, not deployed agents — need to match to deployed IDs
        print(f"File-based icon generation not yet supported. Use --all or --id instead.")
        return


if __name__ == "__main__":
    main()
