from backend.main import app


def test_direct_payment_endpoint_is_not_publicly_exposed() -> None:
    paths = {route.path for route in app.routes}
    assert "/payments/" not in paths
