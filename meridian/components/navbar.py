import reflex as rx

from .brand import brand
from .common import start_button

STEPS = ["Profile", "Documents", "Analysis", "Results", "Report"]


def navbar():
    """Landing navbar: MERIDIAN | How It Works · Journey · About | START JOURNEY."""
    return rx.el.header(
        rx.el.div(
            brand(),
            rx.el.nav(
                rx.el.a("How It Works", href="/#how", class_name="nav-link"),
                rx.el.a("Journey", href="/#journey", class_name="nav-link"),
                rx.el.a("About", href="/#about", class_name="nav-link"),
                class_name="nav-links",
            ),
            start_button("sm"),
            class_name="container nav-inner",
        ),
        class_name="nav",
    )


def journey_nav(active: int):
    """Slim navbar for in-journey pages with a progress stepper."""
    paths = ["/profile", "/documents", "/analysis", "/results", "/report"]
    steps = [
        rx.el.button(
            s,
            on_click=State.navigate_to(paths[i]),
            type="button",
            class_name="step done" if i < active else ("step active" if i == active else "step hide-sm" if i not in (active - 1, active + 1) else "step"),
        )
        for i, s in enumerate(STEPS)
    ]
    return rx.el.header(
        rx.el.div(brand(), rx.el.div(*steps, class_name="stepper"), class_name="container nav-inner"),
        class_name="nav",
    )
