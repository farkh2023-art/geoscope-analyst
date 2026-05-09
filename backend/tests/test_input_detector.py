from app.services.input_detector import detect_input_type
from app.models.schemas import InputType


def test_detect_gps_plain():
    assert detect_input_type("48.8566, 2.3522") == InputType.gps


def test_detect_gps_labeled():
    assert detect_input_type("lat: 48.8566 lon: 2.3522") == InputType.gps


def test_detect_google_maps():
    assert detect_input_type("https://www.google.com/maps/@48.8566,2.3522,15z") == InputType.google_maps_url


def test_detect_osm():
    assert detect_input_type("https://www.openstreetmap.org/#map=12/48.8566/2.3522") == InputType.osm_url


def test_detect_place_name():
    assert detect_input_type("Paris, France") == InputType.place_name


def test_detect_image_extension():
    assert detect_input_type("/uploads/screenshot.png") == InputType.image


def test_detect_image_jpg():
    assert detect_input_type("photo_aerienne.jpg") == InputType.image


def test_detect_free_text():
    result = detect_input_type("La zone industrielle à l'est de la ville")
    assert result == InputType.place_name
