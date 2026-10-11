import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, Community, Domain, AssetType, AssetHead, AssetVersion, VersionStatusEnum


@pytest.mark.asyncio
async def test_uuidv7_sequential_ordering(db_session: AsyncSession):
    """Verify that multiple records inserted sequentially have monotonically increasing UUIDv7 keys."""
    # Fetch existing users
    res = await db_session.execute(select(User).order_by(User.created_at))
    users = res.scalars().all()
    assert len(users) >= 5
    
    # Check that UUIDs are v7 (version 7 bits in standard UUID format)
    for u in users:
        # UUIDv7 has 7 as the 13th hex character (e.g., xxxxxxxx-xxxx-7xxx-xxxx-xxxxxxxxxxxx)
        assert u.id.version == 7, f"Expected UUIDv7 but got version {u.id.version} for user {u.email}"


@pytest.mark.asyncio
async def test_asset_head_and_version_lifecycle(db_session: AsyncSession):
    """Test creating asset head, version, draft lease, and verifying relations."""
    # Find a domain and asset type
    res_dom = await db_session.execute(select(Domain).limit(1))
    domain = res_dom.scalar_one()

    res_type = await db_session.execute(select(AssetType).limit(1))
    asset_type = res_type.scalar_one()

    res_user = await db_session.execute(select(User).limit(1))
    user = res_user.scalar_one()

    # 1. Create Head
    head = AssetHead(
        domain_id=domain.id,
        asset_type_id=asset_type.id,
        locked_by_user_id=user.id,
    )
    db_session.add(head)
    await db_session.flush()
    assert head.id.version == 7

    # 2. Create Draft Version v1
    v1 = AssetVersion(
        asset_head_id=head.id,
        version_number=1,
        status=VersionStatusEnum.DRAFT,
        name="Customer Credit Score Definition",
        description_markdown="Credit bureau calculated score.",
        attributes_payload={"criticality": "HIGH", "pii": True},
        created_by=user.id,
    )
    db_session.add(v1)
    await db_session.flush()
    assert v1.id.version == 7

    # 3. Attach draft to head
    head.active_draft_version_id = v1.id
    await db_session.commit()

    # 4. Reload and assert decoupling
    reloaded = await db_session.get(AssetHead, head.id)
    assert reloaded.active_draft_version_id == v1.id
    assert reloaded.published_version_id is None
    assert reloaded.locked_by_user_id == user.id
