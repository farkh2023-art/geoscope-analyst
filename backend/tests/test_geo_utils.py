from app.services.geo_utils import haversine_m


def test_known_distance_paris_london():
    # Distance Paris (Hôtel de Ville) → Londres (Trafalgar Square), grand cercle ≈ 343,6 km
    d = haversine_m(48.8566, 2.3522, 51.5074, -0.1278)
    expected = 343_556
    assert abs(d - expected) / expected < 0.01


def test_zero_distance_same_point():
    d = haversine_m(48.8566, 2.3522, 48.8566, 2.3522)
    assert d == 0
