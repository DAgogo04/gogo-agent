"""The wake-word matcher is a pure function — so it gets deterministic evals.
Whisper mangles phrases in predictable ways; these cases pin the fuzziness."""

import pytest

from gogo.gateway.voice import matches_wake

SHOULD_WAKE = [
    ("gogo gogo", "gogo gogo"),
    ("Gogo, gogo!", "gogo gogo"),            # punctuation
    ("gogogogo", "gogo gogo"),               # whisper drops the space
    ("so anyway gogo gogo schedule it", "gogo gogo"),  # embedded in speech
    ("cogo gogo", "gogo gogo"),             # one-letter mangle → fuzzy match
    ("Hey Gogo", "hey gogo"),
    ("hey computer, what's up", "hey computer"),
    # regression from the first live session: whisper wrote the wake word in
    # kana — variants after a comma cover other scripts
    ("ゴーゴー", "gogo gogo,ゴーゴー"),
    ("ゴーゴーゴー", "gogo gogo,ゴーゴー"),
    ("小助手你好", "gogo gogo,小助手"),
]

SHOULD_NOT_WAKE = [
    ("what a nice day", "gogo gogo"),
    ("wake up call at nine", "gogo gogo"),
    ("", "gogo gogo"),
    ("gogo gogo", ""),                        # no wake word configured
    ("walk to work", "gogo gogo"),
]


@pytest.mark.parametrize("heard,wake", SHOULD_WAKE, ids=[h for h, _ in SHOULD_WAKE])
def test_wakes(heard, wake):
    assert matches_wake(heard, wake)


@pytest.mark.parametrize("heard,wake", SHOULD_NOT_WAKE, ids=[h or "empty" for h, _ in SHOULD_NOT_WAKE])
def test_stays_asleep(heard, wake):
    assert not matches_wake(heard, wake)
