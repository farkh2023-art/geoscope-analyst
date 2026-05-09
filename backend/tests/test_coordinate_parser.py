import pytest
from app.services.coordinate_parser import parse_coordinates


def test_plain_comma():
    c = parse_coordinates("48.8566, 2.3522")
    assert c is not None
    assert abs(c.lat - 48.8566) < 0.0001
    assert abs(c.lon - 2.3522) < 0.0001


def test_plain_semicolon():
    c = parse_coordinates("48.8566; 2.3522")
    assert c is not None


def test_labeled_format():
    c = parse_coordinates("lat: 48.8566 lon: 2.3522")
    assert c is not None
    assert abs(c.lat - 48.8566) < 0.0001


def test_google_maps_at():
    c = parse_coordinates("https://www.google.com/maps/@48.8566,2.3522,15z")
    assert c is not None
    assert abs(c.lat - 48.8566) < 0.0001


def test_google_maps_q():
    c = parse_coordinates("https://maps.google.com/?q=48.8566,2.3522")
    assert c is not None
    assert abs(c.lat - 48.8566) < 0.0001


def test_negative_coordinates():
    c = parse_coordinates("-33.8688, 151.2093")
    assert c is not None
    assert c.lat < 0


def test_invalid_returns_none():
    assert parse_coordinates("Paris, France") is None


def test_out_of_range_lat():
    assert parse_coordinates("95.0, 2.3522") is None


def test_out_of_range_lon():
    assert parse_coordinates("48.8566, 200.0") is None
