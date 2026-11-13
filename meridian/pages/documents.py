import reflex as rx

from ..components.common import label, primary_button
from ..components.navbar import journey_nav
from ..data import mock
from ..state import State
from .account import notice

_HANDLERS = {
    "resume": State.upload_resume, "transcript": State.upload_transcript,
    "sop": State.upload_sop, "lor": State.upload_lor, "other": State.upload_other,
}


def _slot(d: dict):
    slot, uid = d["slot"], f"up_{d['slot']}"
    empty = rx.el.div(
        label(d["label"], "ink"),
        rx.el.p("Drop a file here", class_name="serif", style={"fontSize": "20px", "fontWeight": 600, "margin": "6px 0 2px"}),
        rx.el.button(
            "Browse files",
            type="button",
            class_name="btn-ghost",
            on_click=rx.call_script(f"document.querySelector('#{uid} input[type=file]').click()"),
        ),
        rx.el.span("PDF, DOCX, TXT, PNG or JPEG · up to 10 MB", style={"fontSize": "13px", "color": "var(--ink-soft)"}),
        class_name="drop",
    )
    filled = rx.el.div(
        rx.el.div(State.docs[f"{slot}_type"], class_name="file-badge"),
        rx.el.div(
            label(d["label"], "blue"),
            rx.el.p(State.docs[f"{slot}_name"], class_name="trunc", style={"margin": "6px 0 4px", "fontWeight": 600}),
            rx.el.div(
                rx.el.span(State.docs[f"{slot}_size"], class_name="mono"),
                rx.el.span(State.docs[f"{slot}_status"], class_name="mono blue", style={"fontWeight": 600}),
                class_name="row", style={"gap": "16px"},
            ),
            style={"minWidth": 0},
        ),
        class_name="doc-card",
    )
    return rx.el.div(
        rx.upload.root(
            rx.cond(State.uploaded_slots.contains(slot), filled, empty),
            id=uid, max_files=1, multiple=False,
            accept={"application/pdf": [".pdf"],
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
                    "text/plain": [".txt"], "image/*": [".png", ".jpg", ".jpeg"]},
            on_drop=_HANDLERS[slot](rx.upload_files(upload_id=uid)),
            class_name="upload-root",
        ),
        rx.cond(
            State.uploaded_slots.contains(slot),
            rx.el.div(
                rx.el.button(
                    rx.cond(State.preview_slot == slot, "Hide preview", "Preview text"),
                    on_click=State.toggle_preview(slot), type="button", class_name="btn-ghost",
                ),
                rx.cond(
                    State.preview_slot == slot,
                    rx.el.p(State.docs[f"{slot}_preview"], class_name="body", style={"marginTop": "12px", "fontSize": "13px"}),
                    rx.fragment(),
                ),
                class_name="stacked", style={"marginTop": "12px"},
            ),
            rx.fragment(),
        ),
        rx.el.p(State.upload_states.get(slot, ""), role="status", class_name="mono"),
        rx.cond(State.upload_errors.get(slot, "") != "", rx.el.p(State.upload_errors.get(slot, ""), " Choose the file again to retry.", role="alert", class_name="field-error"), rx.fragment()),
        rx.cond(
            State.uploaded_slots.contains(slot),
            rx.el.div(rx.el.button("Download", on_click=State.download_document(slot), type="button", class_name="btn-ghost"), rx.el.button("Remove", on_click=State.remove_document(slot), type="button", class_name="btn-ghost"), rx.el.span("Click the card to replace this file.", class_name="mono"), class_name="row wrap"),
            rx.fragment(),
        ),
    )


def documents_page():
    return rx.el.div(
        journey_nav(1),
        notice(),
        rx.el.main(
            rx.el.div(
                rx.el.div(
                    label("Step 2 of 4", "blue"),
                    rx.el.h1("Admissions desk", class_name="h1", style={"marginTop": "10px"}),
                    rx.el.p("Keep your documents in your private dossier. Text is processed into a short preview; image OCR is not available yet, and documents are not used by the prediction models.", class_name="lede", style={"marginTop": "14px"}),
                    class_name="page-enter", style={"marginBottom": "40px"},
                ),
                rx.el.div(
                    rx.el.div(*[_slot(d) for d in mock.DOC_SLOTS], class_name="grid-2"),
                    class_name="sheet sheet-pad stacked", style={"background": "var(--paper)"},
                ),
                rx.el.div(
                    rx.el.div(
                        rx.el.span(State.docs_count, class_name="num-key", style={"fontSize": "40px"}),
                        rx.el.span(f" of {len(mock.DOC_SLOTS)} documents received", class_name="mono"),
                        class_name="row", style={"gap": "10px", "alignItems": "baseline"},
                    ),
                    rx.el.div(

                        primary_button("Start analysis", rx.redirect("/analysis")),
                        class_name="row wrap", style={"gap": "16px"},
                    ),
                    class_name="row wrap between", style={"gap": "20px", "marginTop": "36px"},
                ),
                class_name="container", style={"padding": "56px 28px 96px"},
            ),
        ),
    )
