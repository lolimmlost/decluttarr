import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Track added logging levels
_added_levels = {}


def add_logging_level(level_name, level_num):
    """Dynamically add a custom logging level."""
    if level_name in _added_levels or level_num in _added_levels.values():
        error = f"Logging level '{level_name}' or number '{level_num}' already exists."
        raise ValueError(error)

    logging.addLevelName(level_num, level_name.upper())

    def log_method(self, message, *args, **kwargs):
        if self.isEnabledFor(level_num):
            self.log(level_num, message, *args, **kwargs)

    setattr(logging.Logger, level_name.lower(), log_method)
    setattr(logging, level_name.upper(), level_num)
    _added_levels[level_name] = level_num


# Add custom logging levels
add_logging_level("TRACE", 5)
add_logging_level("VERBOSE", 15)

# Configure the default logger
logger = logging.getLogger(__name__)


def set_handler_format(log_handler, *, long_format=True):
    if long_format:
        target_format = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(message)s", "%Y-%m-%d %H:%M:%S"
        )
    else:
        target_format = logging.Formatter("%(levelname)-7s | %(message)s")
    log_handler.setFormatter(target_format)


# Default console handler
console_handler = logging.StreamHandler()
set_handler_format(console_handler, long_format=True)
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)


def configure_logging(settings):
    """Add a file handler and adjust log levels for all handlers."""
    if settings.envs.in_docker:
        set_handler_format(console_handler, long_format=False)

    log_file = settings.paths.logs
    log_dir = Path(log_file).parent
    Path(log_dir).mkdir(exist_ok=True, parents=True)

    # File handler
    file_handler = RotatingFileHandler(
        log_file, maxBytes=50 * 1024 * 1024, backupCount=2
    )
    set_handler_format(file_handler, long_format=True)
    logger.addHandler(file_handler)

    # Update log level for all handlers
    log_level = getattr(logging, settings.general.log_level.upper(), logging.INFO)
    for handler in logger.handlers:
        handler.setLevel(log_level)
    logger.setLevel(log_level)
