import reflex as rx

config = rx.Config(
    app_name="pepper_reflex",
    telemetry_enabled=False,
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
    state_auto_setters=False,
)
