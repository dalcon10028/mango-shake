import pytest

from shared.utils.iterable import chunks


def test_chunks_empty_list():
    """chunks should return an empty list when input list is empty."""
    assert list(chunks([], 3)) == []


@pytest.mark.parametrize(
    "lst, n, expected",
    [
        ([1, 2, 3, 4, 5, 6], 2, [[1, 2], [3, 4], [5, 6]]),
        ([1, 2, 3, 4, 5], 2, [[1, 2], [3, 4], [5]]),
        ([1, 2, 3], 3, [[1, 2, 3]]),
        ([1, 2], 5, [[1, 2]]),
    ],
)
def test_chunks_various_sizes(lst, n, expected):
    """chunks should split list into correct sized chunks."""
    assert list(chunks(lst, n)) == expected


def test_chunks_invalid_size():
    """chunks should raise ValueError when n is not positive."""
    with pytest.raises(ValueError):
        list(chunks([1, 2, 3], 0))