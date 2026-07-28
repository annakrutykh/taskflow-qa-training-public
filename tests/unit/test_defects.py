import pytest

from app.core.defects import TrainingDefects

pytestmark = pytest.mark.smoke  # без БД, доли секунды — всегда в smoke


def test_empty_string_enables_nothing():
    defects = TrainingDefects("")

    assert not defects.is_enabled("D-01")
    assert not defects.is_enabled("D-02")
    assert not defects.is_enabled("D-04")
    assert not defects.is_enabled("D-17")


def test_parses_comma_separated_list():
    defects = TrainingDefects("D-01,D-17")

    assert defects.is_enabled("D-01")
    assert defects.is_enabled("D-17")
    assert not defects.is_enabled("D-02")
    assert not defects.is_enabled("D-04")


def test_is_case_insensitive():
    defects = TrainingDefects("d-01")

    assert defects.is_enabled("D-01")
    assert defects.is_enabled("d-01")


def test_ignores_whitespace_and_empty_items():
    defects = TrainingDefects(" D-01 , , D-04,")

    assert defects.is_enabled("D-01")
    assert defects.is_enabled("D-04")
    assert not defects.is_enabled("D-02")
