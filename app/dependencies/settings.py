"""
Settings dependencies for FastAPI.
"""

from app.config import get_settings


def get_app_settings():
    """
    애플리케이션 설정 의존성

    Returns:
        Settings: 애플리케이션 설정 객체

    Example:
        @app.get("/config")
        def get_config(settings: Settings = Depends(get_app_settings)):
            return {"app_name": settings.app_name}
    """
    return get_settings()
