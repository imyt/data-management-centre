from fastapi import APIRouter
from app.api.v1 import (
    assets,
    auth,
    communities,
    compliance,
    data_movement,
    domains,
    metamodel,
    policies,
    privacy,
    schema_harvest,
    storage,
    verifications,
    workbench,
    workflows,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(metamodel.router)
api_router.include_router(communities.router)
api_router.include_router(domains.router)
api_router.include_router(assets.router)
api_router.include_router(workflows.router)
api_router.include_router(compliance.router)
api_router.include_router(data_movement.router)
api_router.include_router(workbench.router)
api_router.include_router(storage.router)
api_router.include_router(schema_harvest.router)
api_router.include_router(privacy.router)
api_router.include_router(verifications.router)
api_router.include_router(policies.router)
