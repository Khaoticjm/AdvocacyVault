import reflex as rx
from reflex_base.plugins.sitemap import SitemapPlugin

config = rx.Config(
    app_name="frontend",
    # In prod mode Reflex serves frontend + backend on the same port.
    # Railway exposes a single port; we use 8080 as the unified port.
    backend_port=8080,
    frontend_port=8080,
    plugins=[SitemapPlugin()],
)
