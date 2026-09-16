"""Generate realistic pharmaceutical complaint documents for the demo.

    python samples/make_samples.py

Produces a PDF (API / foreign matter), a second PDF (FDF / packaging defect) and a
raw .eml, so the Document Extraction Tool can be shown against three formats.
All companies, batches and people here are fictional.
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).parent
INK = colors.HexColor("#1f2430")
ACCENT = colors.HexColor("#4f46e5")
RULE = colors.HexColor("#d7dae2")


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=base["Title"], fontSize=16, textColor=INK, spaceAfter=2),
        "sub": ParagraphStyle("s", parent=base["Normal"], fontSize=9, textColor=colors.HexColor("#6b7280")),
        "h": ParagraphStyle("h", parent=base["Heading2"], fontSize=10.5, textColor=ACCENT,
                            spaceBefore=12, spaceAfter=4),
        "p": ParagraphStyle("p", parent=base["Normal"], fontSize=9.5, leading=14,
                            textColor=INK, alignment=TA_LEFT),
    }


def _kv_table(rows):
    t = Table(rows, colWidths=[62 * mm, 103 * mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
    ]))
    return t


def build_pdf(path: Path, header: str, ref: str, blocks: list):
    st = _styles()
    doc = SimpleDocTemplate(str(path), pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
                            leftMargin=22 * mm, rightMargin=22 * mm, title=header)
    story = [Paragraph(header, st["title"]),
             Paragraph("Customer Complaint Notification &nbsp;|&nbsp; Ref: " + ref, st["sub"]),
             Spacer(1, 8)]
    for kind, heading, body in blocks:
        story.append(Paragraph(heading, st["h"]))
        story.append(_kv_table(body) if kind == "kv" else Paragraph(body, st["p"]))
    doc.build(story)
    print("wrote", path.name)


def api_complaint():
    build_pdf(
        OUT / "complaint_metformin_api_foreign_matter.pdf",
        "ZENITH LIFE SCIENCES PVT. LTD.",
        "CC-2026-00154",
        [
            ("kv", "1. Complainant Details", [
                ["Customer / Complainant", "ABC Formulations Ltd."],
                ["Contact Person", "QA Head, Incoming Materials"],
                ["Complaint Received Via", "Email"],
                ["Date of Complaint", "18 July 2026"],
            ]),
            ("kv", "2. Material Identification", [
                ["Product Name", "Metformin Hydrochloride API"],
                ["Grade / Specification", "IP/BP"],
                ["Batch / Lot Number", "MFH260712A"],
                ["Date of Manufacture", "25 June 2026"],
                ["Retest Date", "24 June 2029"],
                ["Quantity Supplied", "500 kg (20 HDPE drums)"],
                ["Quantity Affected", "25 kg (1 HDPE drum)"],
                ["Originating Site Block", "API Block-3, Hyderabad"],
            ]),
            ("p", "3. Description of Complaint",
             "During dispensing of the above batch for granulation, our production team observed "
             "black fibrous foreign particles embedded in the API powder in drum number 14 of 20. "
             "The particles measured approximately 2-4 mm and were visible against the white "
             "crystalline powder. Dispensing was halted immediately and the drum was quarantined "
             "under hold label QH-2026-0881. The remaining 19 drums were visually inspected and "
             "found satisfactory. Photographs and the retained particle sample are available on "
             "request. We request a formal investigation report and replacement of the affected drum."),
            ("kv", "4. Impact Assessment by Complainant", [
                ["Product Released to Market", "No"],
                ["Impacted Non-Product Materials", "Primary packaging - HDPE drum liner"],
                ["Batch Status at Complainant", "Quarantined, production hold"],
            ]),
        ],
    )


def fdf_complaint():
    build_pdf(
        OUT / "complaint_pantoprazole_fdf_packaging.pdf",
        "MERIDIAN HEALTHCARE DISTRIBUTORS",
        "CC-2026-00161",
        [
            ("kv", "1. Complainant Details", [
                ["Customer / Complainant", "Meridian Healthcare Distributors"],
                ["Complaint Received Via", "Distributor Portal"],
                ["Date of Complaint", "02 August 2026"],
            ]),
            ("kv", "2. Product Identification", [
                ["Product Name", "Pantoprazole Sodium Gastro-resistant Tablets"],
                ["Strength", "40 mg"],
                ["Batch / Lot Number", "PNT260521B"],
                ["Manufacturing Date", "May 2026"],
                ["Expiry Date", "April 2028"],
                ["Quantity Affected", "36 blister strips"],
                ["Originating Site Block", "FDF Block-1, Baddi"],
            ]),
            ("p", "3. Description of Complaint",
             "A pharmacy in our distribution network returned 36 blister strips in which the "
             "aluminium foil seal had lifted at the edges, exposing two tablets per strip to ambient "
             "conditions. The affected strips originate from a single shipper carton. Two tablets "
             "showed surface mottling consistent with moisture exposure. No patient has reported an "
             "adverse event. We request investigation of the blister sealing operation and a "
             "replacement consignment."),
            ("kv", "4. Impact Assessment by Complainant", [
                ["Product Released to Market", "Yes - partial recall of shipper in progress"],
                ["Impacted Non-Product Materials", "Primary packaging - Alu-Alu blister foil"],
                ["Adverse Event Reported", "None"],
            ]),
        ],
    )


def email_complaint():
    path = OUT / "complaint_cephalexin_email.eml"
    path.write_text(
        "From: quality@apollopharmacy-example.com\n"
        "To: complaints@zenithlifesciences-example.com\n"
        "Subject: Urgent - Broken and chipped capsules, Cephalexin 250 mg, Batch CPX260408\n"
        "Date: Tue, 11 Aug 2026 09:42:11 +0530\n"
        "Content-Type: text/plain; charset=utf-8\n"
        "\n"
        "Dear Quality Assurance Team,\n"
        "\n"
        "We are writing to formally lodge a customer complaint on behalf of Apollo Pharmacy,\n"
        "Bengaluru Koramangala branch.\n"
        "\n"
        "Product      : Cephalexin Capsules IP\n"
        "Strength     : 250 mg\n"
        "Batch number : CPX260408\n"
        "Mfg date     : April 2026\n"
        "Expiry date  : March 2028\n"
        "Affected qty : 22 capsules across 3 bottles of 100s\n"
        "\n"
        "A walk-in customer returned a sealed bottle in which several capsules were found\n"
        "broken, with loose powder at the bottom of the bottle. Our pharmacist inspected two\n"
        "further bottles from the same shipper and found the same defect. The bottles were\n"
        "sealed and the induction seal was intact, so we do not believe this is handling\n"
        "damage at our end.\n"
        "\n"
        "No adverse event has been reported by the customer. We have withdrawn the remaining\n"
        "stock of this batch from the shelf pending your response, and request a formal\n"
        "investigation along with replacement stock.\n"
        "\n"
        "Regards,\n"
        "Quality Desk, Apollo Pharmacy\n",
        encoding="utf-8",
    )
    print("wrote", path.name)


if __name__ == "__main__":
    api_complaint()
    fdf_complaint()
    email_complaint()
