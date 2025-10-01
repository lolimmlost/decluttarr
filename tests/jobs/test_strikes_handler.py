import logging
from unittest.mock import MagicMock

import pytest

from src.jobs.strikes_handler import StrikesHandler


# pylint: disable=W0212
# pylint: disable=too-many-locals
@pytest.mark.parametrize(
    (
        "download_id",
        "already_in_tracker",
        "in_queue",
        "in_affected_ids",
        "expected_in_tracker",
        "expected_in_paused",
        "expected_in_recovered",
        "expected_in_removed_from_queue",
    ),
    [
        # Not tracked previously, in queue, not affected → ignore
        ("HASH1", False, True, False, False, False, False, False),
        # Previously tracked, no longer in queue and not affected → recover with reason "no longer in queue"
        ("HASH2", True, False, False, False, False, False, True),
        # Previously tracked, still in queue but no longer affected → recover with reason "has recovered"
        ("HASH3", True, True, False, False, False, True, False),
        # Previously tracked, still in queue and still affected → remain tracked, no pause, no recover
        ("HASH4", True, True, True, True, False, False, False),
        # Previously tracked, still in queue, not affected but tracking paused → remain tracked in paused, no recover
        ("HASH5", True, True, False, True, True, False, False),
    ],
)
def test_recover_downloads(
    download_id,
    already_in_tracker,
    in_queue,
    in_affected_ids,
    expected_in_tracker,
    expected_in_paused,
    expected_in_recovered,
    expected_in_removed_from_queue,
):
    # Setup mock tracker with or without the download
    strikes = 1 if already_in_tracker else None
    defective_entry = {
        "title": f"Title-{download_id}",
        "strikes": strikes,
    }
    if expected_in_paused:
        defective_entry["tracking_paused"] = True
        defective_entry["pause_reason"] = "Paused for testing"

    tracker = MagicMock()
    tracker.defective = {
        "remove_stalled": (
            {
                download_id: defective_entry,
            }
            if already_in_tracker
            else {}
        )
    }

    arr = MagicMock()
    arr.tracker = tracker

    handler = StrikesHandler(job_name="remove_stalled", arr=arr, max_strikes=3)

    affected_downloads = []
    if in_affected_ids:
        affected_downloads.append((download_id, {"title": "dummy"}))

    queue = []
    if in_queue:
        queue.append({"downloadId": download_id})

    # Unpack all three returned values from _recover_downloads
    recovered, removed_from_queue, paused = handler._recover_downloads(
        affected_downloads, queue=queue
    )  # pylint: disable=W0212

    is_in_tracker = download_id in tracker.defective["remove_stalled"]
    assert (
        is_in_tracker == expected_in_tracker
    ), f"{download_id} tracker presence mismatch"

    is_in_paused = download_id in paused
    assert is_in_paused == expected_in_paused, f"{download_id} paused presence mismatch"

    is_in_recovered = download_id in recovered
    assert (
        is_in_recovered == expected_in_recovered
    ), f"{download_id} recovered presence mismatch"

    is_in_recovered = download_id in recovered
    assert (
        is_in_recovered == expected_in_recovered
    ), f"{download_id} recovered presence mismatch"

    is_in_removed = download_id in removed_from_queue
    assert (
        is_in_removed == expected_in_removed_from_queue
    ), f"{download_id} removed_from_queue presence mismatch"


@pytest.mark.parametrize(
    ("strikes_before_increment", "max_strikes", "expected_in_affected_downloads"),
    [
        (1, 3, False),  # Below limit   → should not be affected
        (2, 3, False),  # Below limit   → should not be affected
        (3, 3, True),  # At limit, will be pushed over limit   → should be affected
        (4, 3, True),  # Over limit    → should be affected
    ],
)
def test_apply_strikes_and_filter(
    strikes_before_increment, max_strikes, expected_in_affected_downloads
):
    job_name = "remove_stalled"
    tracker = MagicMock()
    tracker.defective = {
        job_name: {"HASH1": {"title": "dummy", "strikes": strikes_before_increment}}
    }

    arr = MagicMock()
    arr.tracker = tracker

    handler = StrikesHandler(job_name=job_name, arr=arr, max_strikes=max_strikes)

    affected_downloads = {
        "HASH1": {"title": "dummy"},
    }

    result = handler._apply_strikes_and_filter(affected_downloads)
    if expected_in_affected_downloads:
        assert "HASH1" in result
    else:
        assert "HASH1" not in result


def test_log_change_logs_expected_strike_changes(caplog):
    handler = StrikesHandler(job_name="remove_stalled", arr=MagicMock(), max_strikes=3)
    handler.tracker = MagicMock()
    handler.tracker.defective = {
        "remove_stalled": {
            "hash_new": {"strikes": 1},
            "hash_inc": {"strikes": 2},
            "hash_paused": {"strikes": 2, "pause_reason": "Bandwidth"},
            "hash_exceed": {"strikes": 10},  # <- add here
        }
    }

    recovered = ["recovered1", "recovered2"]
    removed_from_queue = ["removed"]
    paused = ["hash_paused"]
    strike_exceeds = ["hash_exceed"]

    with caplog.at_level(logging.DEBUG, logger="src.utils.log_setup"):
        handler.log_change(recovered, removed_from_queue, paused, strike_exceeds)

    log_messages = "\n".join(record.message for record in caplog.records)

    # Check category keywords exist
    for keyword in [
        "Added",
        "Incremented",
        "Tracking Paused",
        "Removed from queue",
        "Recovered",
        "Strikes Exceeded",
    ]:
        assert keyword in log_messages

    # Check actual IDs appear somewhere in the logged messages
    for key in ["hash_new", "hash_inc", "hash_exceed", "hash_paused"]:
        assert key in log_messages


@pytest.mark.parametrize(
    "max_strikes, initial_strikes, expected_removed_after_two_runs",
    [
        # max_strikes = 3
        (3, 0, False),  # 0 → 1 → 2
        (3, 1, False),  # 1 → 2 → 3
        (3, 2, True),  # 2 → 3 → 4
        (3, 3, True),  # 3 → 4 → 5
        # max_strikes = 2
        (2, 0, False),  # 0 → 1 → 2
        (2, 1, True),  # 1 → 2 → 3
        (2, 2, True),  # 2 → 3 → 4
        (2, 3, True),  # 3 → 4 → 5
    ],
)
def test_strikes_handler_overall(
    max_strikes, initial_strikes, expected_removed_after_two_runs
):
    """
    Verify that incrementing of strikes works and that
    based on its initial strikes and the max_strikes limit
    removal happens
    Note: The logging output does not show the strike where the removal will be triggered (ie., 4/3 if max strikes = 3)
    Reason: This is on verbose-level, as instead the removal handler then shows another info-level log
    """
    # Set the logger level by name to 15 (VERBOSE)
    logger = logging.getLogger("src.utils.log_setup")
    logger.setLevel(15)

    job_name = "remove_stalled"
    d_id = "some_hash"

    tracker_mock = MagicMock()
    tracker_mock.defective = {
        job_name: {d_id: {"title": "Some Title", "strikes": initial_strikes}}
    }

    arr = MagicMock()
    arr.tracker = tracker_mock

    affected_downloads = {d_id: {"title": "Some Title"}}

    handler = StrikesHandler(job_name=job_name, arr=arr, max_strikes=max_strikes)
    handler.filter_strike_exceeds(affected_downloads.copy(), queue=[])
    result = handler.filter_strike_exceeds(affected_downloads.copy(), queue=[])

    assert (d_id in result) == expected_removed_after_two_runs, (
        f"Expected removed={expected_removed_after_two_runs} for "
        f"initial_strikes={initial_strikes}, max_strikes={max_strikes}, but got {d_id in result}"
    )
