"""`GET /jobs/{id}` and `accepted`, the `202 Accepted` response for routes that start a job."""

import uuid

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from app.core.auth import Permission, Principal, PrincipalDep, Role, can
from app.core.db import SessionDep
from app.core.errors import NotFoundError
from app.core.jobs.models import Job
from app.core.jobs.queue import get_job as find_job
from app.core.jobs.schemas import JobRead, JobResponse
from app.core.schemas import error_responses

router = APIRouter(prefix="/jobs", tags=["platform"])

# Anyone sees the jobs they started; governance also sees everyone's and the scheduler's.
VIEW_ANY_JOB = Permission("view_any_job", {Role.GOVERNANCE})


def can_see(principal: Principal, job: Job) -> bool:
    return job.created_by == principal.actor or can(principal, VIEW_ANY_JOB)


def job_response(job: Job) -> JobResponse:
    # No actions yet: cancelling comes with the first job a user may want to stop.
    return JobResponse(data=JobRead.model_validate(job))


def accepted(request: Request, job: Job) -> JSONResponse:
    """`202 Accepted` with the job and a `Location` to poll. Declare the route with
    `status_code=202, response_model=JobResponse` so the contract shows it."""
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=job_response(job).model_dump(mode="json"),
        headers={"Location": request.app.url_path_for("get_job", job_id=str(job.id))},
    )


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    operation_id="getJob",
    summary="Get a background job's status, progress and result",
    responses=error_responses(401, 404, 422),
)
def get_job(job_id: uuid.UUID, session: SessionDep, principal: PrincipalDep) -> JobResponse:
    job = find_job(session, job_id)
    # Someone else's job answers like a missing one, so ids reveal nothing.
    if job is None or not can_see(principal, job):
        raise NotFoundError("No job has this id.", details={"job_id": job_id})
    return job_response(job)
