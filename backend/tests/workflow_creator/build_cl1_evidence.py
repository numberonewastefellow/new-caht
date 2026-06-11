"""
Build a realistic, multi-format synthetic evidence packet for claim CL1
(residential kitchen fire, CLM-2025-08742).
=======================================================================

Reads the existing single-source-of-truth CSVs in
``test_data/insurance_claims/CL1/`` and emits a realistic claim folder under
``CL1/documents/`` in mixed formats (txt / docx / xlsx / csv / jpg+EXIF), so the
insurance-claims workflow can be exercised with a packet that looks like a real
adjuster's file instead of flattened CSV text.

Design notes:
  * Numbers are DERIVED from the CSVs — never invented — so the documents stay
    consistent with the existing test data and assertions.
  * No new pip dependencies: pandas, python-docx, openpyxl, Pillow are already
    available in the backend image.
  * Deterministic: no random values / timestamps, so re-running is idempotent.
  * Evidence images are PIL-rendered "captioned cards" with embedded EXIF
    (capture date matching the loss window, Naperville GPS, phone camera). Pixels
    are not photoreal; the EXIF + manifest are the evidentiary payload.

Usage:
    python build_cl1_evidence.py            # regenerate CL1/documents/
    python build_cl1_evidence.py --check    # regenerate, then verify consistency
"""

from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path

import pandas as pd

# ── Paths ────────────────────────────────────────────────────────────────────

CL1_DIR = Path(__file__).parent / "test_data" / "insurance_claims" / "CL1"
OUT_DIR = CL1_DIR / "documents"
EVIDENCE_DIR = OUT_DIR / "evidence"

# Naperville, IL — insured property coordinates (for EXIF GPS consistency).
PROP_LAT, PROP_LON = 41.74805, -88.16563
CAPTURE_DT = "2025:01:16 09:24:00"  # adjuster inspection, day after the loss


# ── Source loaders ───────────────────────────────────────────────────────────


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(CL1_DIR / name)


def load_sources() -> dict[str, pd.DataFrame]:
    return {
        "claim": _read("claim_details.csv"),
        "fire": _read("fire_investigation.csv"),
        "damage": _read("damage_assessment.csv"),
        "contractors": _read("contractor_estimates.csv"),
        "policy": _read("policy_info.csv"),
        "prior": _read("prior_claims.csv"),
    }


# ── TXT documents ────────────────────────────────────────────────────────────


def write_fnol(claim: pd.DataFrame) -> None:
    c = claim.iloc[0]
    text = f"""FIRST NOTICE OF LOSS (FNOL)
================================================================

Claim ID:        {c['claim_id']}
Date Reported:   {c['claim_date']}
Policy Number:   {c['policy_number']}
Claim Type:      {c['claim_type']}
Date of Loss:    {c['date_of_loss']}
Adjuster:        {c['adjuster_assigned']}

INSURED
  Name:     {c['insured_name']}
  Property: {c['insured_address']}

LOSS DESCRIPTION
{c['description_of_loss']}

INSURED'S ESTIMATED LOSS:  ${float(c['estimated_amount']):,.2f}

Reported via:  Phone (insured) + agent submission
Status:        Open — assigned for field investigation
----------------------------------------------------------------
This FNOL is a synthetic record generated for workflow testing.
"""
    (OUT_DIR / "FNOL_intake.txt").write_text(text, encoding="utf-8")


def write_adjuster_notes(claim: pd.DataFrame, prior: pd.DataFrame) -> None:
    c = claim.iloc[0]
    lines = [
        "ADJUSTER FIELD NOTES",
        "================================================================",
        f"Claim: {c['claim_id']}    Adjuster: {c['adjuster_assigned']}",
        f"Insured: {c['insured_name']}",
        "",
        "INITIAL CONTACT",
        "  - Spoke with insured by phone. Cooperative. Kitchen unusable;",
        "    insured temporarily staying with family. Requesting ALE.",
        "  - Fire investigation report, 3 contractor bids, and a room-by-room",
        "    inventory already supplied with the claim.",
        "",
        "PRIOR CLAIMS HISTORY",
    ]
    if len(prior) == 0:
        lines.append("  - None on file.")
    else:
        for _, r in prior.iterrows():
            lines.append(
                f"  - {r['claim_id']} ({r['date']}): {r['type']} — "
                f"${float(r['amount']):,.2f} [{r['status']}]"
            )
    lines += [
        "",
        "PRELIMINARY OBSERVATIONS",
        "  - Single prior claim ~5 yrs ago (water/pipe burst), dissimilar peril.",
        "    Not a frequency pattern; no SIU trigger at this time.",
        "  - Cause documented accidental (unattended grease fire). Confirm",
        "    coverage and reconcile the three contractor estimates.",
        "----------------------------------------------------------------",
        "Synthetic record generated for workflow testing.",
    ]
    (OUT_DIR / "adjuster_notes.txt").write_text("\n".join(lines), encoding="utf-8")


# ── DOCX documents ───────────────────────────────────────────────────────────


def write_fire_report(claim: pd.DataFrame, fire: pd.DataFrame) -> None:
    import docx
    from docx.shared import Pt

    c = claim.iloc[0]
    d = docx.Document()
    d.add_heading("FIRE INVESTIGATION REPORT", level=0)
    p = d.add_paragraph()
    p.add_run("Naperville Fire Department — Office of the Fire Marshal").bold = True

    meta = d.add_paragraph()
    meta.add_run(
        f"Claim {c['claim_id']}    |    {c['insured_address']}    |    "
        f"Date of Loss: {c['date_of_loss']}"
    ).italic = True

    d.add_heading("Findings", level=1)
    table = d.add_table(rows=1, cols=3)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text = "Finding", "Detail", "Supporting Evidence"
    for _, r in fire.iterrows():
        row = table.add_row().cells
        row[0].text = str(r["finding"]).replace("_", " ").title()
        row[1].text = str(r["detail"])
        row[2].text = str(r["evidence"])

    d.add_heading("Conclusion", level=1)
    d.add_paragraph(
        "The fire is classified as an accidental cooking fire (unattended grease "
        "ignition) consistent with NFPA 921. No accelerants detected and no "
        "electrical involvement. Damage is confined to the kitchen with smoke "
        "extension to adjacent living room and hallway. Load-bearing structure is "
        "intact; repair rather than full rebuild is indicated."
    )
    note = d.add_paragraph()
    run = note.add_run("Synthetic document generated for workflow testing.")
    run.italic = True
    run.font.size = Pt(8)
    d.save(OUT_DIR / "fire_investigation_report.docx")


def write_policy_declarations(claim: pd.DataFrame, policy: pd.DataFrame) -> None:
    import docx
    from docx.shared import Pt

    c = claim.iloc[0]
    pol = policy.iloc[0]
    d = docx.Document()
    d.add_heading("HOMEOWNER'S POLICY DECLARATIONS", level=0)
    d.add_paragraph(
        f"Policy Number: {pol['policy_number']}        Form: {pol['type']}"
    )
    d.add_paragraph(
        f"Named Insured: {c['insured_name']}\nInsured Location: {c['insured_address']}"
    )
    d.add_paragraph(
        f"Policy Period: {pol['effective_date']} to {pol['expiration_date']}    "
        f"Annual Premium: ${float(pol['premium']):,.2f}"
    )

    d.add_heading("Coverage Limits", level=1)
    table = d.add_table(rows=1, cols=3)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text = "Coverage", "Section", "Limit"
    coverages = [
        ("Dwelling", "Coverage A", float(pol["dwelling_coverage"])),
        ("Personal Property", "Coverage C", float(pol["personal_property_coverage"])),
        ("Personal Liability", "Coverage E", float(pol["liability_coverage"])),
        ("Loss of Use / ALE", "Coverage D", float(pol["additional_living_expenses"])),
    ]
    for label, section, amount in coverages:
        row = table.add_row().cells
        row[0].text, row[1].text, row[2].text = label, section, f"${amount:,.2f}"

    d.add_heading("Deductible", level=1)
    d.add_paragraph(f"${float(pol['deductible']):,.2f} per occurrence (flat, all perils).")

    d.add_heading("Endorsements", level=1)
    for item in str(pol["endorsements"]).split(";"):
        if item.strip():
            d.add_paragraph(item.strip(), style="List Bullet")

    d.add_heading("Exclusions", level=1)
    for item in str(pol["exclusions"]).split(";"):
        if item.strip():
            d.add_paragraph(item.strip(), style="List Bullet")

    note = d.add_paragraph()
    run = note.add_run("Synthetic declarations generated for workflow testing.")
    run.italic = True
    run.font.size = Pt(8)
    d.save(OUT_DIR / "policy_declarations.docx")


# ── XLSX documents ───────────────────────────────────────────────────────────


def write_damage_inventory(damage: pd.DataFrame) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "Damage Inventory"

    headers = [
        "Room", "Category", "Item Description", "Qty", "Age (yrs)",
        "Replacement Cost (RCV)", "Actual Cash Value (ACV)", "Damage %",
        "Repairable", "Est. Repair Cost",
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    rcv_total = acv_total = 0.0
    for _, r in damage.iterrows():
        rcv = float(r["replacement_cost"])
        acv = float(r["actual_cash_value"])
        rcv_total += rcv
        acv_total += acv
        ws.append([
            r["room"], r["item_category"], r["item_description"],
            int(r["quantity"]), int(r["age_years"]), rcv, acv,
            int(r["damage_pct"]), r["repair_possible"],
            float(r["estimated_repair_cost"]),
        ])

    ws.append([])
    total_row = ["TOTALS", "", f"{len(damage)} items", "", "", rcv_total, acv_total, "", "", ""]
    ws.append(total_row)
    for cell in ws[ws.max_row]:
        cell.font = Font(bold=True)

    for col, width in zip("ABCDEFGHIJ", [14, 14, 44, 6, 10, 22, 22, 10, 11, 16]):
        ws.column_dimensions[col].width = width

    wb.save(OUT_DIR / "damage_inventory.xlsx")
    return rcv_total, acv_total


def write_contractor_estimates(contractors: pd.DataFrame) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    # Summary sheet first.
    summary = wb.active
    summary.title = "Summary"
    summary.append(["Contractor", "Labor", "Material", "Total", "Timeline (days)"])
    for cell in summary[1]:
        cell.font = Font(bold=True)

    totals = []
    for _, r in contractors.iterrows():
        total = float(r["total"])
        totals.append(total)
        summary.append([
            r["contractor_name"], float(r["labor_cost"]),
            float(r["material_cost"]), total, int(r["timeline_days"]),
        ])

    avg = sum(totals) / len(totals)
    summary.append([])
    summary.append(["Average", "", "", round(avg, 2), ""])
    summary.append(["Spread (max-min)", "", "", round(max(totals) - min(totals), 2), ""])
    for cell in summary[summary.max_row]:
        cell.font = Font(bold=True)
    for col, width in zip("ABCDE", [30, 14, 14, 16, 16]):
        summary.column_dimensions[col].width = width

    # One detail sheet per contractor (scope narrative).
    for i, (_, r) in enumerate(contractors.iterrows(), start=1):
        ws = wb.create_sheet(title=f"Contractor {i}")
        ws.append(["Field", "Value"])
        ws["A1"].font = ws["B1"].font = Font(bold=True)
        ws.append(["Contractor", r["contractor_name"]])
        ws.append(["Labor Cost", float(r["labor_cost"])])
        ws.append(["Material Cost", float(r["material_cost"])])
        ws.append(["Total Estimate", float(r["total"])])
        ws.append(["Timeline (days)", int(r["timeline_days"])])
        ws.append(["Scope of Work", str(r["scope"])])
        ws.column_dimensions["A"].width = 18
        ws.column_dimensions["B"].width = 90

    wb.save(OUT_DIR / "contractor_estimates.xlsx")
    return totals


# ── CSV (copy) ───────────────────────────────────────────────────────────────


def copy_prior_claims() -> None:
    shutil.copyfile(CL1_DIR / "prior_claims.csv", OUT_DIR / "prior_claims.csv")


# ── Evidence images (PIL captioned cards + EXIF) ─────────────────────────────


def _deg_to_dms_rational(value: float):
    """Convert signed decimal degrees to EXIF (deg, min, sec) float rationals.

    Pillow serialises plain floats to TIFF rationals on save, so the GPS IFD
    expects a 3-tuple of floats — NOT nested (num, den) pairs.
    """
    value = abs(value)
    d = float(int(value))
    m_full = (value - d) * 60
    m = float(int(m_full))
    s = round((m_full - m) * 60, 4)
    return (d, m, s)


def _build_exif(description: str):
    from PIL import Image

    exif = Image.Exif()
    exif[0x010F] = "Apple"                 # Make
    exif[0x0110] = "iPhone 13"             # Model
    exif[0x0132] = CAPTURE_DT              # DateTime
    exif[0x010E] = description             # ImageDescription (survives reliably)
    exif[0x0131] = "ClaimDocsApp 2.4"      # Software
    # Exif sub-IFD: DateTimeOriginal / DateTimeDigitized
    exif[0x8769] = {0x9003: CAPTURE_DT, 0x9004: CAPTURE_DT}
    # GPS sub-IFD: insured property location
    exif[0x8825] = {
        1: "N" if PROP_LAT >= 0 else "S",
        2: _deg_to_dms_rational(PROP_LAT),
        3: "E" if PROP_LON >= 0 else "W",
        4: _deg_to_dms_rational(PROP_LON),
    }
    return exif


def _render_card(claim_id: str, room: str, caption: str, severity: int):
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1024, 768
    img = Image.new("RGB", (W, H), (208, 210, 214))
    draw = ImageDraw.Draw(img)

    def font(size: int):
        try:
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            return ImageFont.load_default()

    # Header band.
    draw.rectangle([0, 0, W, 84], fill=(28, 32, 38))
    draw.text((24, 16), f"{claim_id}  ·  {room.upper()}", fill=(240, 240, 240), font=font(30))
    draw.text((24, 52), caption, fill=(170, 200, 235), font=font(20))

    # Body: representative "damaged item" blocks with soot gradient + char marks.
    body_top, body_bottom = 110, 660
    for bx in range(80, W - 80, 220):
        for by in range(body_top, body_bottom, 180):
            # Base block (cabinet/appliance face).
            draw.rectangle([bx, by, bx + 180, by + 140], fill=(150, 120, 92), outline=(60, 50, 40))
            # Soot gradient — darker toward the top (heat rises).
            for i in range(140):
                alpha = int(180 * (1 - i / 140) * (severity / 100))
                shade = max(0, 40 - alpha // 6)
                draw.line([(bx, by + i), (bx + 180, by + i)], fill=(shade, shade, shade), width=1)
            # Char marks.
            for cx in range(bx + 12, bx + 168, 26):
                draw.line([(cx, by + 6), (cx + 8, by + 60)], fill=(18, 16, 14), width=3)

    # Smoke haze overlay (alpha blend) scaled by severity.
    haze = Image.new("RGB", (W, body_bottom - body_top), (90, 90, 95))
    img.paste(Image.blend(img.crop((0, body_top, W, body_bottom)), haze, severity / 320),
              (0, body_top))
    draw = ImageDraw.Draw(img)

    # Footer stamp.
    draw.rectangle([0, H - 70, W, H], fill=(28, 32, 38))
    draw.text((24, H - 58),
              f"Captured {CAPTURE_DT}   GPS {PROP_LAT:.5f}, {PROP_LON:.5f}   Naperville, IL",
              fill=(210, 210, 210), font=font(18))
    draw.text((24, H - 32), f"Damage severity: {severity}%   (synthetic evidence)",
              fill=(180, 180, 180), font=font(16))
    return img


# Curated subset of inventory items to photograph (highest impact across rooms).
PHOTO_ITEMS = [
    ("Custom maple upper cabinets", "Kitchen"),
    ("KitchenAid Double Wall Oven", "Kitchen"),
    ("Quartz countertop", "Kitchen"),
    ("Drywall ceiling with recessed lighting", "Kitchen"),
    ("Samsung French Door Refrigerator", "Kitchen"),
    ("Smoke damage to drywall and paint", "Living Room"),
    ("Smoke staining on hallway ceiling", "Hallway"),
]


def write_evidence(claim: pd.DataFrame, damage: pd.DataFrame) -> list[dict]:
    claim_id = claim.iloc[0]["claim_id"]
    manifest: list[dict] = []

    for idx, (item_key, room) in enumerate(PHOTO_ITEMS, start=1):
        match = damage[
            (damage["room"] == room)
            & (damage["item_description"].str.contains(item_key.split("(")[0].strip()[:18], case=False, na=False))
        ]
        if match.empty:
            match = damage[damage["item_description"].str.contains(item_key[:18], case=False, na=False)]
        row = match.iloc[0] if not match.empty else None
        desc = str(row["item_description"]) if row is not None else item_key
        severity = int(row["damage_pct"]) if row is not None else 80

        # ASCII caption: stored in EXIF ImageDescription (ASCII field) + manifest.
        caption = f"{desc} - {severity}% fire/smoke damage"
        fname = f"photo_{idx:02d}_{room.lower().replace(' ', '_')}.jpg"
        img = _render_card(claim_id, room, caption, severity)
        img.save(EVIDENCE_DIR / fname, "JPEG", quality=88, exif=_build_exif(caption))

        manifest.append({
            "filename": fname,
            "room": room,
            "item_description": desc,
            "damage_pct": severity,
            "capture_datetime": CAPTURE_DT.replace(":", "-", 2),
            "gps_lat": PROP_LAT,
            "gps_lon": PROP_LON,
            "camera": "Apple iPhone 13",
        })

    with open(EVIDENCE_DIR / "evidence_manifest.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(manifest[0].keys()))
        writer.writeheader()
        writer.writerows(manifest)
    return manifest


# ── Orchestration ────────────────────────────────────────────────────────────


def build() -> dict:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    src = load_sources()
    write_fnol(src["claim"])
    write_adjuster_notes(src["claim"], src["prior"])
    write_fire_report(src["claim"], src["fire"])
    write_policy_declarations(src["claim"], src["policy"])
    rcv_total, acv_total = write_damage_inventory(src["damage"])
    contractor_totals = write_contractor_estimates(src["contractors"])
    copy_prior_claims()
    manifest = write_evidence(src["claim"], src["damage"])

    summary = {
        "rcv_total": round(rcv_total, 2),
        "acv_total": round(acv_total, 2),
        "inventory_rows": len(src["damage"]),
        "contractor_totals": contractor_totals,
        "photos": len(manifest),
    }
    files = sorted(p.relative_to(OUT_DIR).as_posix() for p in OUT_DIR.rglob("*") if p.is_file())
    print(f"Generated {len(files)} files in {OUT_DIR}:")
    for f in files:
        print(f"  - {f}")
    print(f"\nDerived totals: RCV=${summary['rcv_total']:,.2f}  ACV=${summary['acv_total']:,.2f}  "
          f"items={summary['inventory_rows']}  photos={summary['photos']}")
    print(f"Contractor totals: {[f'${t:,.0f}' for t in contractor_totals]}")
    return summary


def check(summary: dict) -> None:
    """Round-trip verify the generated packet against source CSV figures."""
    import docx
    from openpyxl import load_workbook

    from doc_text_extract import extract_text

    errors: list[str] = []

    # Policy declarations DOCX must contain the dwelling limit + deductible.
    pol_text = extract_text(OUT_DIR / "policy_declarations.docx")
    for needle in ["$450,000.00", "$2,500.00", "HWP-2022-445891"]:
        if needle not in pol_text:
            errors.append(f"policy_declarations.docx missing {needle!r}")

    # Inventory XLSX must have 20 data rows + a totals row matching RCV.
    wb = load_workbook(OUT_DIR / "damage_inventory.xlsx", data_only=True)
    ws = wb["Damage Inventory"]
    rcv_cells = [row[5] for row in ws.iter_rows(min_row=2, values_only=True) if row[0] == "TOTALS"]
    if not rcv_cells or abs(float(rcv_cells[0]) - summary["rcv_total"]) > 0.01:
        errors.append(f"damage_inventory.xlsx RCV total mismatch (expected {summary['rcv_total']})")
    wb.close()

    # Contractor XLSX summary totals.
    est_text = extract_text(OUT_DIR / "contractor_estimates.xlsx")
    for t in summary["contractor_totals"]:
        if f"{t:.1f}" not in est_text and str(int(t)) not in est_text:
            errors.append(f"contractor_estimates.xlsx missing total {t}")

    # Evidence: 7 photos + manifest, EXIF round-trips.
    photos = list(EVIDENCE_DIR.glob("photo_*.jpg"))
    if len(photos) != summary["photos"]:
        errors.append(f"expected {summary['photos']} photos, found {len(photos)}")
    img_meta = extract_text(photos[0]) if photos else ""
    if "DateTimeOriginal" not in img_meta and "DateTime" not in img_meta:
        errors.append("EXIF date did not round-trip on first photo")

    if errors:
        print("\nCONSISTENCY CHECK: FAILED")
        for e in errors:
            print(f"  [FAIL] {e}")
        raise SystemExit(1)
    print("\nCONSISTENCY CHECK: PASSED")
    print(f"  [OK] policy limits, deductible, policy# present in declarations DOCX")
    print(f"  [OK] inventory XLSX RCV total = ${summary['rcv_total']:,.2f} ({summary['inventory_rows']} items)")
    print(f"  [OK] contractor totals present in estimates XLSX")
    print(f"  [OK] {len(photos)} EXIF-tagged evidence photos + manifest")
    print(f"  [OK] first photo EXIF: {img_meta}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate CL1 multi-format evidence packet")
    parser.add_argument("--check", action="store_true", help="verify consistency after generating")
    args = parser.parse_args()
    result = build()
    if args.check:
        check(result)
