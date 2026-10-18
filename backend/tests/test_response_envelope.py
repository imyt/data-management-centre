from fastapi.routing import APIRoute, iter_route_contexts

from app.core.config import Settings
from app.core.schemas import Envelope
from app.main import create_app


def _api_routes() -> list[APIRoute]:
    """Every operation in the app, including those in included routers."""
    app = create_app(Settings(_env_file=None))
    originals = (context.original_route for context in iter_route_contexts(app.routes))
    return [route for route in originals if isinstance(route, APIRoute)]


# Operations whose responses are not resources and so skip the envelope. Keep this list short.
EXEMPT = {
    "getHealth",  # liveness probe, read by infrastructure
    "getHealthReady",  # readiness probe, read by infrastructure
    "getMeta",  # pairing check, read before the app knows it talks to the right API (ADR 0004 §5)
}


def test_every_route_returns_the_envelope() -> None:
    routes = _api_routes()
    missing = [
        r.operation_id
        for r in routes
        if r.operation_id not in EXEMPT
        and not (isinstance(r.response_model, type) and issubclass(r.response_model, Envelope))
    ]

    assert routes
    assert missing == [], f"Response models must inherit app.core.schemas.Envelope: {missing}"


def test_exemptions_are_real_routes() -> None:
    operation_ids = {r.operation_id for r in _api_routes()}

    assert EXEMPT.issubset(operation_ids)
