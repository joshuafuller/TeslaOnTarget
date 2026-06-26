"""Immutable application configuration loaded from a user ``config.py`` file.

The container's entrypoint writes ``config.py`` with UPPER_SNAKE module-level
names (``COT_URL``, ``API_LOOP_DELAY``, ...). :func:`load_config` reads those into
a frozen :class:`AppConfig` (defaults for anything absent), which is then injected
into the components that need it -- no global mutable state.
"""
import importlib.util
import logging
import os
from dataclasses import dataclass, fields, replace
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AppConfig:
    """Immutable runtime configuration."""

    cot_url: str = "tcp://YOUR-TAK-SERVER:8085"
    tesla_username: Optional[str] = None
    api_loop_delay: int = 10
    dead_reckoning_delay: int = 1
    dead_reckoning_enabled: bool = False
    last_position_file: str = "last_known_position.json"
    debug_mode: bool = False
    vehicle_filter: Tuple[str, ...] = ()
    health_no_send_seconds: int = 0
    health_check_interval: int = 0
    health_hard_restart_seconds: int = 0
    health_file: str = "health.json"
    # Optional push-notification endpoint (ntfy topic / generic webhook). Empty
    # disables alerting -- so silent failures stay silent unless one is supplied.
    alert_webhook_url: str = ""

    def validate(self) -> bool:
        """True when the required fields are present."""
        if not self.tesla_username:
            logger.error("TESLA_USERNAME not configured")
            return False
        if not self.cot_url:
            logger.error("COT_URL not configured")
            return False
        return True


def _resolve_config_path(config_path: Optional[str]) -> str:
    """Resolve the config path to use (explicit arg > env var > package-adjacent)."""
    if config_path is None:
        # An explicit path (set by the container) decouples loading from where the
        # package is installed; only honor it when the file exists so a mis-set env
        # var falls back to the package-adjacent config.py rather than defaults.
        env_path = os.environ.get("TESLAONTARGET_CONFIG")
        if env_path:
            env_path = os.path.expanduser(env_path)
            if os.path.isfile(env_path):
                return env_path
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(parent_dir, "config.py")
    return os.path.expanduser(config_path)


def _load_config_module(config_path: str):
    """Execute the user config.py directly (no sys.path mutation); None on failure."""
    spec = importlib.util.spec_from_file_location("teslaontarget_user_config", config_path)
    if spec is None or spec.loader is None:
        logger.error(f"Could not build an import spec for {config_path}")
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _coerce_vehicle_filter(value) -> Tuple[str, ...]:
    """Normalize a configured VEHICLE_FILTER to a tuple of names.

    A bare string is treated as a single name (not split into characters); a
    non-iterable is ignored (empty filter) so one bad value can't discard the
    rest of an otherwise-valid config.
    """
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    try:
        return tuple(value)
    except TypeError:
        logger.warning("VEHICLE_FILTER is not a list or string; ignoring it")
        return ()


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """Load configuration into an immutable :class:`AppConfig` (defaults if absent)."""
    config_path = _resolve_config_path(config_path)
    if not os.path.isfile(config_path):
        logger.warning(f"Config file not found at {config_path}, using defaults")
        return AppConfig()
    try:
        module = _load_config_module(config_path)
        if module is None:
            return AppConfig()
        overrides = {}
        for field in fields(AppConfig):
            key = field.name.upper()
            if hasattr(module, key):
                value = getattr(module, key)
                if field.name == "vehicle_filter":
                    value = _coerce_vehicle_filter(value)
                overrides[field.name] = value
        logger.info(f"Configuration loaded from {config_path}")
        return replace(AppConfig(), **overrides)
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        return AppConfig()
