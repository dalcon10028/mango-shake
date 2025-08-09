import sys
import pytest
from datetime import date
from shared.utils.date_utils import get_base_date, get_start_end_dates

@pytest.fixture(autouse=True)
def fix_today(monkeypatch):
    # Freeze today's date to 2025-08-10 for deterministic testing
    class DummyDate(date):
        @classmethod
        def today(cls):
            return cls(2025, 8, 10)

    monkeypatch.setattr('shared.utils.date_utils.date', DummyDate)

@pytest.mark.parametrize(
    'argv, expected',
    [
        (['prog'], date(2025, 8, 9)),  # default to yesterday
        (['prog', '--base_date', '2025-08-08'], date(2025, 8, 8)),
    ]
)
def test_get_base_date_valid(monkeypatch, argv, expected):
    monkeypatch.setattr(sys, 'argv', argv)
    assert get_base_date() == expected


def test_get_base_date_invalid_format(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['prog', '--base_date', '08-10-2025'])
    with pytest.raises(ValueError):
        get_base_date()


def test_get_base_date_invalid_date(monkeypatch):
    # Invalid calendar date should raise ValueError
    monkeypatch.setattr(sys, 'argv', ['prog', '--base_date', '2025-02-30'])
    with pytest.raises(ValueError):
        get_base_date()


@pytest.mark.parametrize(
    "argv, expected_start, expected_end",
    [
        (["prog"], date(2025, 8, 9), date(2025, 8, 9)),  # defaults to yesterday for both
        (["prog", "--start_date", "2025-08-01"], date(2025, 8, 1), date(2025, 8, 9)),
        (["prog", "--end_date", "2025-08-05"], date(2025, 8, 9), date(2025, 8, 5)),
        (
            ["prog", "--start_date", "2025-08-02", "--end_date", "2025-08-04"],
            date(2025, 8, 2),
            date(2025, 8, 4),
        ),
    ],
)
def test_get_start_end_dates_valid(monkeypatch, argv, expected_start, expected_end):
    monkeypatch.setattr(sys, "argv", argv)
    assert get_start_end_dates() == (expected_start, expected_end)


def test_get_start_end_dates_invalid_format(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--start_date", "08-01-2025"])
    with pytest.raises(ValueError):
        get_start_end_dates()


def test_get_start_end_dates_start_after_end(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--start_date", "2025-08-05", "--end_date", "2025-08-01"])
    with pytest.raises(ValueError):
        get_start_end_dates()
