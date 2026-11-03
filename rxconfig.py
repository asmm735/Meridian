import os

import reflex as rx

api_url = (
    os.environ.get("REFLEX_API_URL")
    or os.environ.get("RENDER_EXTERNAL_URL")
    or "http://127.0.0.1:8000"
)

config = rx.Config(
    app_name="meridian",
    api_url=api_url,
    show_built_with_reflex=False,
    disable_plugins=[rx.plugins.SitemapPlugin],
)
