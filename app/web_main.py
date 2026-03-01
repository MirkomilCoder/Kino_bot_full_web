from __future__ import annotations

import uvicorn

from .config import load_settings
from .web_app import create_fastapi_app


def main() -> None:
    settings = load_settings()
    if not settings.web_admin_enabled:
        raise RuntimeError("WEB_ADMIN_ENABLED=0. Admin web app o'chirilgan.")
    app = create_fastapi_app()
    uvicorn.run(app, host=settings.web_host, port=settings.web_port, proxy_headers=True, forwarded_allow_ips="*")


if __name__ == "__main__":
    main()
