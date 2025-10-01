import inspect

from src.utils.log_setup import logger


def validate_data_types(cls, default_cls=None):
    """
    Ensure all attributes match expected types dynamically.

    If default_cls is provided, the default key is taken from this class rather than the own class
    If the attribute doesn't exist in `default_cls`, fall back to `cls.__class__`.

    """

    def _unhandled_conversion():
        error = f"Unhandled type conversion for '{attr}': {expected_type}"
        raise TypeError(error)

    annotations = inspect.get_annotations(cls.__class__)  # Extract type hints

    for attr, expected_type in annotations.items():
        if not hasattr(cls, attr):  # Skip if attribute is missing
            continue

        value = getattr(cls, attr)
        default_source = (
            default_cls if default_cls and hasattr(default_cls, attr) else cls.__class__
        )
        default_value = getattr(default_source, attr, None)

        if value == default_value:
            continue

        if not isinstance(value, expected_type):
            try:
                if expected_type is bool:
                    value = convert_to_bool(value)
                elif expected_type is int:
                    value = int(value)
                elif expected_type is float:
                    value = float(value)
                elif expected_type is str:
                    value = convert_to_str(value)
                elif expected_type is list:
                    value = convert_to_list(value)
                elif expected_type is dict:
                    value = convert_to_dict(value)
                else:
                    _unhandled_conversion()
            except Exception as e:  # noqa: BLE001
                logger.error(
                    f"❗️ Invalid type for '{attr}': Expected {expected_type.__name__}, but got {type(value).__name__}. "
                    f"Error: {e}. Using default value: {default_value}",
                )
                value = default_value

        setattr(cls, attr, value)


# --- Helper Functions ---
def convert_to_bool(raw_value):
    """Convert strings like 'yes', 'no', 'true', 'false' into boolean values."""
    if isinstance(raw_value, bool):
        return raw_value

    true_values = {"1", "yes", "true", "on"}
    false_values = {"0", "no", "false", "off"}

    if isinstance(raw_value, str):
        raw_value = raw_value.strip().lower()

    if raw_value in true_values:
        return True
    if raw_value in false_values:
        return False
    error = f"Invalid boolean value: '{raw_value}'"
    raise ValueError(error)


def convert_to_str(raw_value):
    """Ensure a string and trims whitespace."""
    if isinstance(raw_value, str):
        return raw_value.strip()
    return str(raw_value).strip()


def convert_to_list(raw_value):
    """Ensure a value is a list."""
    if isinstance(raw_value, list):
        return [convert_to_str(item) for item in raw_value]
    return [convert_to_str(raw_value)]  # Wrap single values in a list


def convert_to_dict(raw_value):
    """Ensure a value is a dictionary."""
    if isinstance(raw_value, dict):
        return {convert_to_str(k): v for k, v in raw_value.items()}
    error = f"Expected dict but got {type(raw_value).__name__}"
    raise TypeError(error)
