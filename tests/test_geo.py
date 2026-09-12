from atalaya.core.geo import assess_relative_position, bearing_to_cardinal_es
from atalaya.core.models import GeoPoint


def test_bearing_to_cardinal_es() -> None:
    assert bearing_to_cardinal_es(0) == "norte"
    assert bearing_to_cardinal_es(44) == "noreste"
    assert bearing_to_cardinal_es(91) == "este"
    assert bearing_to_cardinal_es(181) == "sur"


def test_assess_relative_position_for_demo_casevac() -> None:
    command = GeoPoint(lat=4.7100, lon=-74.0800)
    target = GeoPoint(lat=4.7111, lon=-74.0721)

    geo = assess_relative_position(command, target)

    assert 870 <= geo.distance_m <= 890
    assert geo.relative_direction == "este"
