import reflex as rx

from ..components.common import label
from ..components.navbar import journey_nav
from ..data import profile as mock
from .account import notice
from ..data.profile import COUNTRIES, REGIONS
from ..state import State


def _on_change(key: str):
    return lambda v: State.set_field(key, v)


def _field(f: dict):
    key, kind = f["key"], f["kind"]
    if key == "regions":
        control = rx.el.div(
            rx.el.input(default_value=State.region_query, on_change=State.set_region_query, list="region-options", class_name="input", id=f"f-{key}", placeholder="Search and choose a state or region"),
            rx.el.datalist(*[rx.el.option(value=v) for v in REGIONS], id="region-options"),
            rx.el.button("Add region", on_click=State.add_region, type="button", class_name="btn-ghost"),
            rx.el.button("Clear all regions", on_click=State.clear_regions, type="button", class_name="btn-ghost", disabled=State.regions.length() == 0),
            rx.el.div(rx.foreach(State.regions, lambda r: rx.el.button(r, " ×", on_click=State.remove_region(r), type="button", aria_label="Remove " + r)), class_name="region-chips"))
    elif key in ("nationality", "country"):
        control = rx.el.div(rx.el.input(default_value=State.profile[key], on_change=_on_change(key), list=f"options-{key}", id=f"f-{key}", class_name="input", placeholder="Search countries"),
            rx.el.datalist(*[rx.el.option(value=v) for v in COUNTRIES], id=f"options-{key}"))
    elif kind == "select":
        opts = list(f["options"])
        control = rx.el.select(
            rx.el.option("Choose…", value=""),
            *[rx.el.option(o, value=o) for o in opts],

            default_value=State.profile[key],
            on_change=_on_change(key),
            class_name="input", id=f"f-{key}",
        )
    elif kind == "textarea":
        control = rx.el.textarea(
            default_value=State.profile[key], placeholder=f["placeholder"],
            on_change=_on_change(key), class_name="input", id=f"f-{key}",
        )
    else:
        control = rx.el.input(
            default_value=State.profile[key], placeholder=f["placeholder"], type=kind,
            on_change=_on_change(key), class_name="input", id=f"f-{key}",
        )
    field = rx.el.div(
        rx.el.label("Preferred regions (select multiple)" if key == "regions" else f["label"], html_for=f"f-{key}", class_name="field-label"),
        control,
        rx.el.small(
            "Required for university matching · saved in your dossier"
            if key in ("match_country", "match_tier")
            else "Optional · saved in your dossier",
            class_name="mono",
        ),
        rx.el.p(State.field_errors.get(key, ""), class_name="field-error", role="status"),
        class_name="field wide" if f["wide"] else "field",
    )
    if key == "essay_score":
        return rx.cond(State.profile["degree_goal"] == "MBA", field, rx.fragment())
    return field


def _panel(i: int, section: dict):
    content = rx.el.div(
        rx.el.div(
            label(f"Section {i + 1} of {len(mock.FORM_SCHEMA)}", "blue"),
            rx.el.h2(section["label"], class_name="h2", style={"marginTop": "8px"}),
            style={"margin": "8px 0 28px"},
        ),
        rx.el.div(*[_field(f) for f in section["fields"]], class_name="form-grid"),
        rx.el.p(
            "Agent 7 needs all eight structured achievement fields. Use documented scores from 0 to 10; "
            "uploads and free text are not converted into scores. Leave unknown values blank; enter 0 only "
            "for known absence. These inputs produce synthetic-rubric strength, not admission chances.",
            class_name="notice",
        ) if section["id"] == "experience" else rx.fragment(),
        class_name="page-enter",
    )
    return rx.el.div(
        rx.cond(State.profile_tab == i, content, rx.fragment()),
        class_name="profile-panel",
    )


_TAB_LABELS = {"tests": "Tests", "goals": "Goals", "intake": "Intake", "programs": "Programs"}


def _tab(i: int, section: dict):
    return rx.el.button(
        f"{i + 1:02d}  {_TAB_LABELS.get(section['id'], section['label'])}",
        on_click=State.set_tab(i), type="button",
        class_name=rx.cond(State.profile_tab == i, "doc-tab active", "doc-tab"),
    )


def _summary():
    return rx.el.aside(
        rx.el.div(
            label("Dossier status", "blue"),
            rx.el.p(State.student_name, class_name="h3", style={"margin": "12px 0 4px"}),
            rx.el.p(State.target_program, class_name="body"),
            rx.el.hr(class_name="rule", style={"margin": "22px 0"}),
            label("Profile complete"),
            rx.el.p(State.completion_str, class_name="num-key", style={"fontSize": "54px", "margin": "8px 0 12px"}),
            rx.el.div(rx.el.i(style={"width": State.completion_str}), class_name="progress"),
            rx.el.p("Completion reflects seven core dossier fields. Analysis explains which inputs its API needs.", class_name="body", style={"marginTop": "18px", "fontSize": "13px"}),
            class_name="sheet sheet-pad stacked",
        ),
        style={"position": "sticky", "top": "100px"},
    )


def profile_page():
    return rx.el.div(
        journey_nav(0),
        notice(),
        rx.el.span(custom_attrs={"data-unsaved-profile": rx.cond(State.profile_dirty, "true", "false")}, style={"display":"none"}),
        rx.el.div(rx.el.button(rx.cond(State.saving, "Saving…", "Save changes"), on_click=State.save_profile, disabled=State.saving, class_name="tab-button"), rx.el.button("Cancel", on_click=State.cancel_profile, disabled=State.saving, class_name="btn-ghost"), rx.el.span(rx.cond(State.profile_dirty, "Unsaved changes", "All changes saved"), role="status"), class_name="container row wrap", style={"gap":"16px", "paddingTop":"24px"}),
        rx.el.main(
            rx.el.div(
                rx.el.div(
                    label("Step 1 of 4", "blue"),
                    rx.el.h1("Student profile", class_name="h1", style={"marginTop": "10px"}),
                    rx.el.p("Fill in your dossier section by section. Next section keeps your draft and moves forward. Save changes or Continue to documents saves it; Cancel restores the last saved version.", class_name="lede", style={"marginTop": "14px"}),
                    style={"marginBottom": "36px"}, class_name="page-enter",
                ),
                rx.el.div(
                    rx.el.div(
                        rx.el.div(*[_tab(i, s) for i, s in enumerate(mock.FORM_SCHEMA)], class_name="tabs", role="tablist"),
                        rx.el.div(
                            *[_panel(i, s) for i, s in enumerate(mock.FORM_SCHEMA)],
                            notice(),
                            rx.el.div(
                                rx.el.button("Back", on_click=State.prev_tab, type="button", class_name="btn-ghost",
                                             style={"visibility": rx.cond(State.profile_tab == 0, "hidden", "visible")}),
                                rx.el.button(
                                    rx.el.span(rx.cond(State.profile_tab == len(mock.FORM_SCHEMA) - 1, "Continue to documents", "Next section")),
                                    rx.el.span("→", class_name="tab-arrow"),
                                    on_click=State.next_tab, type="button", class_name="tab-button",
                                ),
                                class_name="row wrap between", style={"gap": "12px", "marginTop": "40px", "paddingTop": "24px", "borderTop": "1px solid var(--rule)"},
                            ),
                            class_name="sheet sheet-pad", style={"borderTopLeftRadius": "0", "marginTop": "-1px"},
                        ),
                    ),
                    _summary(),
                    class_name="split", style={"gridTemplateColumns": "minmax(0,2.3fr) minmax(0,1fr)"},
                ),
                class_name="container", style={"padding": "56px 28px 96px"},
            ),
        ),
    )
