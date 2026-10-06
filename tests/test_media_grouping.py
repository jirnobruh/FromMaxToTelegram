"""
Tests for splitting media into chunks of 10 items max.
"""
from src.formatter import split_into_media_batches


def test_split_empty():
    assert split_into_media_batches([]) == []


def test_split_under_ten():
    items = list(range(5))
    batches = split_into_media_batches(items, batch_size=10)
    assert len(batches) == 1
    assert batches[0] == [0, 1, 2, 3, 4]


def test_split_exact_ten():
    items = list(range(10))
    batches = split_into_media_batches(items, batch_size=10)
    assert len(batches) == 1
    assert len(batches[0]) == 10


def test_split_twenty_five():
    items = list(range(25))
    batches = split_into_media_batches(items, batch_size=10)
    assert len(batches) == 3
    assert len(batches[0]) == 10
    assert len(batches[1]) == 10
    assert len(batches[2]) == 5
