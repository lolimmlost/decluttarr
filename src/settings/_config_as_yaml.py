import yaml


def mask_sensitive_value(value, key, sensitive_attributes):
    """Mask the value if it's in the sensitive attributes."""
    return "*****" if key in sensitive_attributes else value


def filter_internal_attributes(data, internal_attributes, hide_internal_attr):
    """Filter out internal attributes based on the hide_internal_attr flag."""
    return {
        k: v
        for k, v in data.items()
        if not (hide_internal_attr and k in internal_attributes)
    }


def clean_dict(data, sensitive_attributes, internal_attributes, hide_internal_attr):
    """Clean a dictionary by masking sensitive attributes and filtering internal ones."""
    masked = {
        k: mask_sensitive_value(v, k, sensitive_attributes) for k, v in data.items()
    }
    return filter_internal_attributes(masked, internal_attributes, hide_internal_attr)


def clean_list(obj, sensitive_attributes, internal_attributes, hide_internal_attr):
    """Clean a list of dicts or class instances."""
    cleaned_list = []
    for entry in obj:
        if isinstance(entry, dict):
            cleaned_list.append(
                clean_dict(
                    entry, sensitive_attributes, internal_attributes, hide_internal_attr
                )
            )
        elif hasattr(entry, "__dict__"):
            cleaned_list.append(
                clean_dict(
                    vars(entry),
                    sensitive_attributes,
                    internal_attributes,
                    hide_internal_attr,
                )
            )
        else:
            cleaned_list.append(entry)
    return cleaned_list


def clean_object(obj, sensitive_attributes, internal_attributes, hide_internal_attr):
    """Clean an object (either a dict, class instance, or other types)."""
    if isinstance(obj, dict):
        return clean_dict(
            obj, sensitive_attributes, internal_attributes, hide_internal_attr
        )
    if hasattr(obj, "__dict__"):
        return clean_dict(
            vars(obj), sensitive_attributes, internal_attributes, hide_internal_attr
        )

    return obj


def get_config_as_yaml(
    data,
    sensitive_attributes=None,
    internal_attributes=None,
    *,
    hide_internal_attr=True,
):
    """Process the configuration into YAML format."""
    if sensitive_attributes is None:
        sensitive_attributes = set()
    if internal_attributes is None:
        internal_attributes = set()

    config_output = {}

    for key, obj in data.items():
        if key.startswith("_"):
            continue

        # Process list-based config
        if isinstance(obj, list):
            cleaned_list = clean_list(
                obj,
                sensitive_attributes,
                internal_attributes,
                hide_internal_attr,
            )
            if cleaned_list:
                config_output[key] = cleaned_list

        # Process dict or class-like object config
        else:
            if not key in internal_attributes and hide_internal_attr:
                cleaned_obj = clean_object(
                    obj,
                    sensitive_attributes,
                    internal_attributes,
                    hide_internal_attr,
                )
                config_output[key] = cleaned_obj

    return yaml.dump(
        config_output, indent=2, default_flow_style=False, sort_keys=False
    ).strip()
