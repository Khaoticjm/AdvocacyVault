import reflex as rx

config = rx.Config(
    app_name="frontend",
    api_url="http://localhost:8001",
    frontend_port=3000,
    backend_port=8000,
    env=rx.Env.DEV,
    tailwind=None,
)
