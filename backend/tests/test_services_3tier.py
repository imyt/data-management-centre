"""Direct tests for Pragmatic 3-Tier Services (AssetService, WorkflowService, ComplianceService)."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.entities.workflow import TaskDecision
from app.domain.exceptions import (
    ConcurrencyLockException,
    EntityNotFoundException,
    UnauthorizedDraftModificationException,
    ValidationException,
)
from app.models.metamodel import AssetType, RelationType
from app.models.organization import Domain
from app.models.user import User
from app.models.workflow import WorkflowDefinition
from app.services import (
    AssetService,
    ComplianceService,
    WorkflowService,
)


@pytest.mark.asyncio
async def test_3tier_asset_service_full_lifecycle(db_session: AsyncSession):
    """Test AssetService creation, draft lock, diff, publication, and lineage directly."""
    service = AssetService(db_session)

    # 1. Fetch domain, type, and user
    dom = (await db_session.execute(select(Domain))).scalars().first()
    atype = (await db_session.execute(select(AssetType))).scalars().first()
    user = (await db_session.execute(select(User))).scalars().first()

    assert dom and atype and user

    # 2. Create Asset
    head = await service.create_asset(
        domain_id=dom.id,
        asset_type_id=atype.id,
        name="Tier 3 Service Asset",
        user_id=user.id,
        description_markdown="Initial draft description for 3-tier testing.",
        attributes_payload={"CONFIDENTIALITY": "INTERNAL"},
    )
    assert head.id is not None
    assert head.active_draft_version is not None
    assert head.active_draft_version.version_number == 1

    # 3. Publish initial draft
    published = await service.publish_draft(head.id, user.id)
    assert published.version_number == 1
    assert published.status.value == "PUBLISHED"

    # 4. Fork draft (v2)
    draft_v2 = await service.acquire_or_fork_draft(head.id, user.id)
    assert draft_v2.version_number == 2
    assert draft_v2.status.value == "DRAFT"

    # 5. Update draft v2
    updated = await service.update_draft(
        head.id,
        user.id,
        name="Tier 3 Service Asset (Updated)",
        description_markdown="Extended description with more than 50 characters to satisfy governance requirements.",
        attributes_payload={"CONFIDENTIALITY": "RESTRICTED", "PII": True},
    )
    assert updated.name == "Tier 3 Service Asset (Updated)"

    # 6. Generate visual diff
    diff = await service.get_visual_diff(head.id)
    assert diff.has_changes is True
    assert diff.name_diff["changed"] is True

    # 7. Publish v2
    pub_v2 = await service.publish_draft(head.id, user.id)
    assert pub_v2.version_number == 2
    assert pub_v2.status.value == "PUBLISHED"

    # 8. Check version history
    history = await service.get_version_history(head.id)
    assert len(history) == 2
    assert history[0].version_number == 2

    # 9. Lineage graph (root node)
    lineage = await service.get_lineage_graph(head.id, max_depth=1)
    assert lineage.root_asset_head_id == head.id
    assert len(lineage.nodes) >= 1


@pytest.mark.asyncio
async def test_3tier_workflow_service_lifecycle(db_session: AsyncSession):
    """Test WorkflowService starting pipeline, task listing, and approval progression."""
    wf_service = WorkflowService(db_session)
    asset_service = AssetService(db_session)

    dom = (await db_session.execute(select(Domain))).scalars().first()
    atype = (await db_session.execute(select(AssetType))).scalars().first()
    user = (await db_session.execute(select(User))).scalars().first()
    wdef = (await db_session.execute(select(WorkflowDefinition))).scalars().first()

    assert dom and atype and user and wdef

    # Create an asset with an active draft
    head = await asset_service.create_asset(
        domain_id=dom.id,
        asset_type_id=atype.id,
        name="Workflow Managed Metric",
        user_id=user.id,
        description_markdown="Metrics definition for approval.",
        attributes_payload={"CONFIDENTIALITY": "INTERNAL"},
    )

    # Start workflow
    instance = await wf_service.start_workflow(head.id, wdef.id, user.id)
    assert instance.status.value == "RUNNING"
    assert len(instance.tasks) == 1

    task = instance.tasks[0]
    assert task.decision.value == "PENDING"

    # Action task: Approve
    actioned = await wf_service.action_task(
        task_id=task.id,
        decision=TaskDecision.APPROVED,
        decided_by=user.id,
        decision_notes="Approved via 3-Tier test",
    )
    assert actioned.decision.value == "APPROVED"


@pytest.mark.asyncio
async def test_3tier_compliance_service_scan_and_fix(db_session: AsyncSession):
    """Test ComplianceService scanning policies and one-click auto-fixing."""
    compliance_service = ComplianceService(db_session)
    asset_service = AssetService(db_session)

    dom = (await db_session.execute(select(Domain))).scalars().first()
    atype = (await db_session.execute(select(AssetType))).scalars().first()
    user = (await db_session.execute(select(User))).scalars().first()

    # Create asset with intentional policy violations (short description, no PII, no confidentiality)
    head = await asset_service.create_asset(
        domain_id=dom.id,
        asset_type_id=atype.id,
        name="Violating Asset",
        user_id=user.id,
        description_markdown="Short",
        attributes_payload={},
    )

    # Run Scan
    scan_res = await compliance_service.scan_policies(actor_id=user.id, domain_id=dom.id)
    assert scan_res.scanned_assets_count > 0
    assert scan_res.issues_detected_count > 0

    # Find an open issue for our asset
    issues = await compliance_service.list_issues(asset_id=head.id)
    assert len(issues) >= 1
    target_issue = issues[0]

    # Remediate issue
    resolved = await compliance_service.remediate_issue(target_issue.id, resolved_by_user_id=user.id)
    assert resolved.status.value == "RESOLVED"
    assert resolved.resolved_at is not None


@pytest.mark.asyncio
async def test_3tier_asset_concurrency_lease_and_locks(db_session: AsyncSession):
    """Test concurrent draft acquisition, lease violation, and lock release."""
    service = AssetService(db_session)

    dom = (await db_session.execute(select(Domain))).scalars().first()
    atype = (await db_session.execute(select(AssetType))).scalars().first()
    users = (await db_session.execute(select(User))).scalars().all()
    user1 = users[0]
    user2 = users[1]

    # User 1 creates asset
    head = await service.create_asset(
        domain_id=dom.id,
        asset_type_id=atype.id,
        name="Concurrency Test Asset",
        user_id=user1.id,
        description_markdown="Testing concurrency lease locks.",
    )

    # User 1 holds lease
    assert head.locked_by_user_id == user1.id

    # User 2 attempts to acquire/fork draft while locked -> ConcurrencyLockException
    with pytest.raises(ConcurrencyLockException):
        await service.acquire_or_fork_draft(head.id, user2.id)

    # User 2 attempts to update draft -> UnauthorizedDraftModificationException
    with pytest.raises(UnauthorizedDraftModificationException):
        await service.update_draft(head.id, user2.id, name="Illegal Update")

    # User 1 releases lock
    released = await service.release_lock(head.id, user1.id)
    assert released is True

    # User 2 now acquires draft successfully
    draft2 = await service.acquire_or_fork_draft(head.id, user2.id)
    assert draft2.id is not None
    head_updated = await service.get_asset_head(head.id)
    assert head_updated.locked_by_user_id == user2.id


@pytest.mark.asyncio
async def test_3tier_asset_lineage_graph_traversal_and_cycles(db_session: AsyncSession):
    """Test multi-hop BFS traversal, relation linking, and cycle prevention."""
    service = AssetService(db_session)

    dom = (await db_session.execute(select(Domain))).scalars().first()
    atype = (await db_session.execute(select(AssetType))).scalars().first()
    user = (await db_session.execute(select(User))).scalars().first()
    rel_type = (await db_session.execute(select(RelationType))).scalars().first()

    # Create 3 assets in a triangle cycle: A -> B -> C -> A
    asset_a = await service.create_asset(domain_id=dom.id, asset_type_id=atype.id, name="Node A", user_id=user.id)
    asset_b = await service.create_asset(domain_id=dom.id, asset_type_id=atype.id, name="Node B", user_id=user.id)
    asset_c = await service.create_asset(domain_id=dom.id, asset_type_id=atype.id, name="Node C", user_id=user.id)

    # Publish drafts so they appear in lineage with names
    await service.publish_draft(asset_a.id, user.id)
    await service.publish_draft(asset_b.id, user.id)
    await service.publish_draft(asset_c.id, user.id)

    # Link relations
    await service.add_relation(asset_a.id, asset_b.id, rel_type.id, user.id)
    await service.add_relation(asset_b.id, asset_c.id, rel_type.id, user.id)
    await service.add_relation(asset_c.id, asset_a.id, rel_type.id, user.id)

    # Traverse lineage from Node A with depth 3 (must not enter infinite loop)
    graph = await service.get_lineage_graph(asset_a.id, max_depth=3)
    node_ids = {n.id for n in graph.nodes}
    assert asset_a.id in node_ids
    assert asset_b.id in node_ids
    assert asset_c.id in node_ids
    assert len(graph.edges) >= 3


@pytest.mark.asyncio
async def test_3tier_workflow_rejection_and_invalid_transitions(db_session: AsyncSession):
    """Test workflow task rejection, already decided validation, and entity not found."""
    wf_service = WorkflowService(db_session)
    asset_service = AssetService(db_session)

    dom = (await db_session.execute(select(Domain))).scalars().first()
    atype = (await db_session.execute(select(AssetType))).scalars().first()
    user = (await db_session.execute(select(User))).scalars().first()
    wdef = (await db_session.execute(select(WorkflowDefinition))).scalars().first()

    head = await asset_service.create_asset(
        domain_id=dom.id, asset_type_id=atype.id, name="Rejectable Asset", user_id=user.id
    )
    instance = await wf_service.start_workflow(head.id, wdef.id, user.id)
    task = instance.tasks[0]

    # Reject the task
    actioned = await wf_service.action_task(
        task_id=task.id,
        decision=TaskDecision.REJECTED,
        decided_by=user.id,
        decision_notes="Rejection test",
    )
    assert actioned.decision.value == "REJECTED"

    # Actioning an already decided task raises ValidationException
    with pytest.raises(ValidationException):
        await wf_service.action_task(
            task_id=task.id,
            decision=TaskDecision.APPROVED,
            decided_by=user.id,
        )

    # Actioning a nonexistent task raises EntityNotFoundException
    import uuid
    with pytest.raises(EntityNotFoundException):
        await wf_service.action_task(
            task_id=uuid.uuid4(),
            decision=TaskDecision.APPROVED,
            decided_by=user.id,
        )


@pytest.mark.asyncio
async def test_3tier_asset_validation_and_not_found(db_session: AsyncSession):
    """Test AssetService validation errors and non-existent lookups."""
    service = AssetService(db_session)
    dom = (await db_session.execute(select(Domain))).scalars().first()
    atype = (await db_session.execute(select(AssetType))).scalars().first()
    user = (await db_session.execute(select(User))).scalars().first()

    # Empty name raises ValidationException
    with pytest.raises(ValidationException):
        await service.create_asset(
            domain_id=dom.id,
            asset_type_id=atype.id,
            name="   ",
            user_id=user.id,
        )

    # Non-existent asset raises EntityNotFoundException
    import uuid
    with pytest.raises(EntityNotFoundException):
        await service.get_asset_head(uuid.uuid4())

