import sys
import re
from collections import namedtuple

import mock
import pytest

sys.modules["discord"] = mock.MagicMock()
sys.modules["discord.ext"] = mock.MagicMock()

from ikabot.entrybanner import MemberMatcher


FakeMember = namedtuple("FakeMember", ["name"])


def test_member_matcher_enabled():
    """Test if enabled works correctly."""
    mm = MemberMatcher(None, True, None)
    assert(mm.enabled)

    mm.disable()
    assert(not mm.enabled)

    mm.enable()
    assert(mm.enabled)


@pytest.mark.parametrize(
    ("is_enabled", "string", "expected"),
    [
        (True, "aaa", True),
        (True, "aaaa", True),
        (True, "baa", False),
        (True, "Aaa", False),
        (False, "aaa", False),
        (False, "aaaa", False),
        (False, "baa", False),
        (False, "Aaa", False),
    ]
)
def test_member_matcher_call(is_enabled, string, expected):
    """Test if the matcher call works and it honors the enabled flag."""
    mm = MemberMatcher(re.compile("aaa"), is_enabled, None)
    assert(mm(FakeMember(string)) == expected)
