from src.settings._jobs import JobParams


def test_job_params_truthiness_is_false_by_default():
    assert not JobParams()


def test_job_params_truthiness_reflects_enabled_flag():
    assert JobParams(enabled=True)
    assert not JobParams(enabled=False)
