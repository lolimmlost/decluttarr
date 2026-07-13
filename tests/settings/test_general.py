from src.settings._general import General


def test_request_timeout_defaults_to_15_seconds():
    general = General({})

    assert general.request_timeout == 15.0


def test_request_timeout_accepts_numeric_strings():
    general = General({"general": {"request_timeout": "42"}})

    assert general.request_timeout == 42.0
