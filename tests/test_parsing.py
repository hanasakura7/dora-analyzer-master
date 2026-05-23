from dora_analyzer.collect_issues import has_excluded_label, is_bug_issue
from dora_analyzer.git_utils import is_semver_like_tag


def test_semver_tag_detection() -> None:
    assert is_semver_like_tag("v0.7.0")
    assert is_semver_like_tag("0.7.0")
    assert is_semver_like_tag("v1.2.3-beta.1")
    assert not is_semver_like_tag("release-2024")


def test_bug_label_detection() -> None:
    assert is_bug_issue(["bug"])
    assert is_bug_issue(["type:bug"])
    assert is_bug_issue(["confirmed bug"])
    assert not is_bug_issue(["enhancement"])


def test_excluded_label_detection() -> None:
    assert has_excluded_label(["duplicate"])
    assert has_excluded_label(["not planned"])
    assert not has_excluded_label(["bug"])
