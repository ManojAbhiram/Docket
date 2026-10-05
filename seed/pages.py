"""HTML for each synthetic document. Rendered to PNG by `seed.render`."""

from html import escape

from seed.dataset import Application, DocumentRecord

_TITLES = {
    "10th_marksheet": "Secondary School Examination, Class X: Statement of Marks",
    "12th_marksheet": "Senior School Certificate Examination, Class XII: Statement of Marks",
    "id_proof": "Identity Card",
    "transfer_certificate": "School Transfer Certificate",
}
_NUMBER_LABELS = {"id_proof": "ID number", "transfer_certificate": "TC number"}

_STYLE = """
body { font-family: 'DejaVu Serif', serif; background: #fdfcf7; margin: 0; padding: 40px;
       width: 720px; color: #1b1b1b; }
h1 { font-size: 20px; text-align: center; border-bottom: 2px solid #1b1b1b; padding-bottom: 8px; }
table { width: 100%; border-collapse: collapse; margin-top: 16px; }
td, th { border: 1px solid #555; padding: 6px 10px; font-size: 15px; text-align: left; }
.label { width: 38%; background: #f0eee4; }
.footer { margin-top: 28px; font-size: 12px; text-align: center; color: #8a1c1c; }
"""


def render_html(doc: DocumentRecord, app: Application) -> str:
    """One self-contained HTML page for a document."""
    rows = [("Name", doc.printed_name)]
    if doc.printed_father_name is not None:
        rows.append(("Father's name", doc.printed_father_name))
    rows.append(("Date of birth", doc.printed_dob))
    if doc.printed_board is not None:
        rows.append(("Board", doc.printed_board))
    if doc.printed_roll_number is not None:
        rows.append(("Roll number", doc.printed_roll_number))
    if doc.printed_id_number is not None:
        rows.append((_NUMBER_LABELS[doc.doc_type], doc.printed_id_number))
    body = "".join(
        f'<tr><td class="label">{escape(label)}</td><td>{escape(value)}</td></tr>'
        for label, value in rows
    )
    marks = ""
    if doc.printed_marks is not None:
        marks_rows = "".join(
            f"<tr><td>{escape(subject)}</td><td>{mark}</td></tr>"
            for subject, mark in doc.printed_marks.items()
        )
        marks = f"<table><tr><th>Subject</th><th>Marks</th></tr>{marks_rows}</table>"
    footer = f"SAMPLE, SYNTHETIC DOCUMENT, NOT A REAL RECORD ({escape(app.application_id)})"
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{_STYLE}</style></head><body>"
        f"<h1>{escape(_TITLES[doc.doc_type])}</h1>"
        f"<table>{body}</table>{marks}"
        f"<p class='footer'>{footer}</p>"
        "</body></html>"
    )
