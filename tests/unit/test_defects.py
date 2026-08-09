import pytest

from app.core.defects import TrainingDefects

pytestmark = pytest.mark.smoke  # без БД, доли секунды — всегда в smoke


def test_empty_string_disables_nothing():
    defects = TrainingDefects("")

    assert defects.is_enabled("D-01")
    assert defects.is_enabled("D-02")
    assert defects.is_enabled("D-04")
    assert defects.is_enabled("D-17")
    assert defects.is_enabled("D-18")


def test_parses_comma_separated_list_as_denylist():
    defects = TrainingDefects("D-01,D-17")

    assert not defects.is_enabled("D-01")
    assert not defects.is_enabled("D-17")
    assert defects.is_enabled("D-02")
    assert defects.is_enabled("D-04")


def test_is_case_insensitive():
    defects = TrainingDefects("d-01")

    assert not defects.is_enabled("D-01")
    assert not defects.is_enabled("d-01")


def test_ignores_whitespace_and_empty_items():
    defects = TrainingDefects(" D-01 , , D-04,")

    assert not defects.is_enabled("D-01")
    assert not defects.is_enabled("D-04")
    assert defects.is_enabled("D-02")


def test_all_sentinel_disables_everything():
    defects = TrainingDefects("ALL")

    assert not defects.is_enabled("D-01")
    assert not defects.is_enabled("D-18")
    # даже дефект, не существующий на момент написания теста — сентинел
    # не завязан на конкретный список ID.
    assert not defects.is_enabled("D-99")


def test_all_sentinel_is_case_insensitive_and_combinable():
    defects = TrainingDefects("all, D-01")

    assert not defects.is_enabled("D-01")
    assert not defects.is_enabled("D-17")
