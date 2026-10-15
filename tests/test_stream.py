"""The web server's stream resume (ui/server.py): where a reconnecting browser continues."""

from ui.server import _resume_from


def test_resume_from_the_last_event_id():
    assert _resume_from("5", 10) == 5


def test_resume_is_clamped_to_what_exists():
    assert _resume_from("50", 10) == 10
    assert _resume_from("-3", 10) == 0


def test_a_missing_or_garbled_id_replays_from_the_start():
    assert _resume_from(None, 10) == 0
    assert _resume_from("abc", 10) == 0
