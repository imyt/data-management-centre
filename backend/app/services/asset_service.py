"""Service Tier: Cohesive domain service managing curated catalog assets.

Encapsulates asset lifecycle, exclusive concurrency lease locks, visual diffing,
semantic relation mapping, and multi-hop lineage graph DAG traversal.
"""
from collections import deque
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities.diff import generate_version_diff
from app.domain.exceptions import (
    ConcurrencyLockException,
    DraftNotFoundException,
    EntityNotFoundException,
    UnauthorizedDraftModificationException,
    ValidationException,
)
from app.domain.validation.attribute_validator import validate_asset_attributes
from app.models.asset import AssetHead, AssetRelation, AssetVersion, VersionStatusEnum
from app.models.metamodel import AssetType, AssetTypeAttributeAssignment
from app.models.user import User
from app.schemas.asset import DiffResponse
from app.schemas.lineage import LineageEdgeRead, LineageGraphRead, LineageNodeRead


class AssetService:
    """Cohesive business logic service for catalog assets, drafts, locks, and lineage."""

    DEFAULT_LEASE_SECONDS = 300  # 5-minute optimistic concurrency lease

    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------------------------------------------------------
    # Core Queries
    # -------------------------------------------------------------------------

    async def get_asset_head(
        self, asset_head_id: uuid.UUID, for_update: bool = False
    ) -> AssetHead:
        """Fetch asset head with eagerly loaded versions and locking user."""
        stmt = (
            select(AssetHead)
            .options(
                selectinload(AssetHead.published_version),
                selectinload(AssetHead.active_draft_version),
                selectinload(AssetHead.locked_by_user),
            )
            .where(AssetHead.id == asset_head_id)
        )
        if for_update:
            stmt = stmt.with_for_update()

        result = await self.db.execute(stmt)
        head = result.scalar_one_or_none()
        if not head:
            raise EntityNotFoundException(f"Asset head '{asset_head_id}' not found.")
        return head

    async def list_assets(
        self,
        domain_id: Optional[uuid.UUID] = None,
        asset_type_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[AssetHead]:
        """Query catalog asset heads with optional domain, type, status, and search filters."""
        stmt = (
            select(AssetHead)
            .options(
                selectinload(AssetHead.published_version),
                selectinload(AssetHead.active_draft_version),
                selectinload(AssetHead.locked_by_user),
            )
            .order_by(AssetHead.created_at.desc())
        )

        if domain_id:
            stmt = stmt.where(AssetHead.domain_id == domain_id)
        if asset_type_id:
            stmt = stmt.where(AssetHead.asset_type_id == asset_type_id)

        result = await self.db.execute(stmt)
        heads = list(result.scalars().all())

        # Filter by status or text search across active version
        filtered: List[AssetHead] = []
        for h in heads:
            active_version = h.active_draft_version or h.published_version
            if not active_version:
                continue

            # Status filter
            if status and active_version.status.value.upper() != status.upper():
                continue

            # Text search filter (case-insensitive substring match on name / description)
            if search:
                query = search.strip().lower()
                name_match = query in active_version.name.lower()
                desc_match = bool(
                    active_version.description_markdown
                    and query in active_version.description_markdown.lower()
                )
                if not (name_match or desc_match):
                    continue

            filtered.append(h)

        return filtered[skip : skip + limit]

    # -------------------------------------------------------------------------
    # Creation & Lifecycle Mutations
    # -------------------------------------------------------------------------

    async def create_asset(
        self,
        domain_id: uuid.UUID,
        asset_type_id: uuid.UUID,
        name: str,
        user_id: uuid.UUID,
        description_markdown: Optional[str] = None,
        attributes_payload: Optional[Dict[str, Any]] = None,
    ) -> AssetHead:
        """Create a new asset head and its initial version (v1 DRAFT)."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValidationException("Asset name cannot be empty.")

        attributes_payload = dict(attributes_payload or {})

        # Validate attributes against asset type schema if assignments exist
        await self._validate_attributes_for_type(asset_type_id, attributes_payload)

        now = datetime.now(timezone.utc)
        head_id = uuid.uuid7()
        version_id = uuid.uuid7()

        # 1. Create Asset Head initially without active_draft_version_id
        head = AssetHead(
            id=head_id,
            domain_id=domain_id,
            asset_type_id=asset_type_id,
            published_version_id=None,
            active_draft_version_id=None,
            locked_by_user_id=user_id,
            locked_at=now,
            created_at=now,
        )
        self.db.add(head)
        await self.db.flush()

        # 2. Create Initial Draft Version (v1)
        version = AssetVersion(
            id=version_id,
            asset_head_id=head_id,
            version_number=1,
            status=VersionStatusEnum.DRAFT,
            name=clean_name,
            description_markdown=description_markdown,
            attributes_payload=attributes_payload,
            relations_snapshot=[],
            created_by=user_id,
            created_at=now,
        )
        self.db.add(version)
        await self.db.flush()

        # 3. Point Head to active draft version
        head.active_draft_version_id = version_id
        await self.db.commit()
        return await self.get_asset_head(head_id)

    async def acquire_or_fork_draft(
        self,
        asset_head_id: uuid.UUID,
        user_id: uuid.UUID,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> AssetHead:
        """Acquire exclusive editing lease, forking a new draft from published if none active."""
        head = await self.get_asset_head(asset_head_id, for_update=True)
        now = datetime.now(timezone.utc)

        # 1. Verify exclusive concurrency lease
        if head.locked_by_user_id and head.locked_by_user_id != user_id:
            lease_expiry = head.locked_at + timedelta(seconds=lease_seconds)
            if now < lease_expiry:
                holder = head.locked_by_user.full_name if head.locked_by_user else str(head.locked_by_user_id)
                raise ConcurrencyLockException(
                    f"Asset '{asset_head_id}' is locked by {holder} until {lease_expiry.isoformat()}."
                )

        draft: AssetVersion
        # 2. If no active working draft exists, fork one from published version
        if not head.active_draft_version_id:
            pub = head.published_version
            if not pub and head.published_version_id:
                pub = await self.db.get(AssetVersion, head.published_version_id)

            if not pub:
                raise ValidationException("Cannot fork draft: Asset has no published baseline.")
            new_version_id = uuid.uuid7()
            draft = AssetVersion(
                id=new_version_id,
                asset_head_id=head.id,
                version_number=pub.version_number + 1,
                status=VersionStatusEnum.DRAFT,
                name=pub.name,
                description_markdown=pub.description_markdown,
                attributes_payload=dict(pub.attributes_payload or {}),
                relations_snapshot=list(pub.relations_snapshot or []),
                created_by=user_id,
                created_at=now,
            )
            self.db.add(draft)
            await self.db.flush()
            head.active_draft_version_id = new_version_id
            head.active_draft_version = draft
        else:
            draft = await self.db.get(AssetVersion, head.active_draft_version_id)
            if not draft:
                raise DraftNotFoundException("Active draft could not be loaded.")
            head.active_draft_version = draft

        # 3. Grant / renew lease
        head.locked_by_user_id = user_id
        head.locked_at = now

        await self.db.commit()
        await self.db.refresh(draft)
        return draft

    async def update_draft(
        self,
        asset_head_id: uuid.UUID,
        user_id: uuid.UUID,
        name: Optional[str] = None,
        description_markdown: Optional[str] = None,
        attributes_payload: Optional[Dict[str, Any]] = None,
    ) -> AssetVersion:
        """Update active draft version while holding editing lease."""
        head = await self.get_asset_head(asset_head_id, for_update=True)
        if not head.active_draft_version_id:
            raise DraftNotFoundException(f"No active draft found for asset '{asset_head_id}'.")

        # Verify lease ownership
        if head.locked_by_user_id and head.locked_by_user_id != user_id:
            raise UnauthorizedDraftModificationException(
                "You do not hold the active draft lock for this asset."
            )

        draft = head.active_draft_version
        if not draft:
            result = await self.db.execute(
                select(AssetVersion).where(AssetVersion.id == head.active_draft_version_id)
            )
            draft = result.scalar_one_or_none()
            if not draft:
                raise DraftNotFoundException("Draft version entity could not be retrieved.")

        # Update fields if provided
        if name is not None:
            clean_name = name.strip()
            if not clean_name:
                raise ValidationException("Asset name cannot be empty.")
            draft.name = clean_name

        if description_markdown is not None:
            draft.description_markdown = description_markdown

        if attributes_payload is not None:
            await self._validate_attributes_for_type(head.asset_type_id, attributes_payload)
            draft.attributes_payload = attributes_payload

        # Refresh lease timestamp
        head.locked_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(draft)
        return draft

    async def release_lock(
        self, asset_head_id: uuid.UUID, user_id: uuid.UUID, force: bool = False
    ) -> bool:
        """Release the editing lease on an asset."""
        head = await self.get_asset_head(asset_head_id, for_update=True)
        if not head.locked_by_user_id:
            return True

        if not force and head.locked_by_user_id != user_id:
            raise UnauthorizedDraftModificationException("Cannot release a lock held by another user.")

        head.locked_by_user_id = None
        head.locked_at = None
        await self.db.commit()
        return True

    async def publish_draft(
        self, asset_head_id: uuid.UUID, user_id: uuid.UUID
    ) -> AssetVersion:
        """Promote active working draft to immutable published version."""
        head = await self.get_asset_head(asset_head_id, for_update=True)
        if not head.active_draft_version_id:
            raise DraftNotFoundException(f"No active draft found to publish for asset '{asset_head_id}'.")

        draft = head.active_draft_version
        if not draft:
            result = await self.db.execute(
                select(AssetVersion).where(AssetVersion.id == head.active_draft_version_id)
            )
            draft = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        # 1. Supersede previously published version if one exists
        if head.published_version_id:
            prev_result = await self.db.execute(
                select(AssetVersion).where(AssetVersion.id == head.published_version_id)
            )
            prev_pub = prev_result.scalar_one_or_none()
            if prev_pub:
                prev_pub.status = VersionStatusEnum.SUPERSEDED

        # 2. Promote draft to PUBLISHED
        draft.status = VersionStatusEnum.PUBLISHED
        draft.published_at = now

        # 3. Update Head pointer and clear lock
        head.published_version = draft
        head.published_version_id = draft.id
        head.active_draft_version = None
        head.active_draft_version_id = None
        head.locked_by_user_id = None
        head.locked_at = None

        await self.db.commit()
        await self.db.refresh(draft)
        return draft

    # -------------------------------------------------------------------------
    # Visual Semantic Diff & Audit Ledger
    # -------------------------------------------------------------------------

    async def get_visual_diff(self, asset_head_id: uuid.UUID) -> DiffResponse:
        """Generate side-by-side visual diff between active working draft and published version."""
        head = await self.get_asset_head(asset_head_id)
        if not head.active_draft_version and head.active_draft_version_id:
            head.active_draft_version = await self.db.get(AssetVersion, head.active_draft_version_id)
        if not head.published_version and head.published_version_id:
            head.published_version = await self.db.get(AssetVersion, head.published_version_id)

        if not head.active_draft_version:
            raise DraftNotFoundException(f"No active draft exists for asset '{asset_head_id}'.")

        raw_diff = generate_version_diff(head.published_version, head.active_draft_version)

        return DiffResponse(
            asset_head_id=head.id,
            published_version_number=head.published_version.version_number if head.published_version else None,
            draft_version_number=head.active_draft_version.version_number,
            name_diff=raw_diff.name_diff,
            description_diff=raw_diff.description_diff,
            attributes_diff=raw_diff.attributes_diff,
            relations_diff=raw_diff.relations_diff,
            has_changes=raw_diff.has_changes,
        )

    async def get_version_history(self, asset_head_id: uuid.UUID) -> List[AssetVersion]:
        """Retrieve chronological immutable ledger of all versions for this asset."""
        stmt = (
            select(AssetVersion)
            .where(AssetVersion.asset_head_id == asset_head_id)
            .order_by(AssetVersion.version_number.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # Semantic Relations & Lineage Graph DAG
    # -------------------------------------------------------------------------

    async def add_relation(
        self,
        source_asset_head_id: uuid.UUID,
        target_asset_head_id: uuid.UUID,
        relation_type_id: uuid.UUID,
        created_by_user_id: uuid.UUID,
    ) -> AssetRelation:
        """Link two asset heads with a directed semantic relationship."""
        if source_asset_head_id == target_asset_head_id:
            raise ValidationException("An asset cannot be related to itself.")

        # Ensure both source and target exist
        await self.get_asset_head(source_asset_head_id)
        await self.get_asset_head(target_asset_head_id)

        relation = AssetRelation(
            id=uuid.uuid7(),
            source_asset_head_id=source_asset_head_id,
            target_asset_head_id=target_asset_head_id,
            relation_type_id=relation_type_id,
            created_by=created_by_user_id,
        )
        self.db.add(relation)
        await self.db.commit()
        await self.db.refresh(relation)
        return relation

    async def list_relations(
        self, asset_head_id: uuid.UUID, direction: str = "outgoing"
    ) -> List[AssetRelation]:
        """List semantic relations for asset head (outgoing, incoming, or both)."""
        stmt = select(AssetRelation)
        if direction == "outgoing":
            stmt = stmt.where(AssetRelation.source_asset_head_id == asset_head_id)
        elif direction == "incoming":
            stmt = stmt.where(AssetRelation.target_asset_head_id == asset_head_id)
        else:
            stmt = stmt.where(
                or_(
                    AssetRelation.source_asset_head_id == asset_head_id,
                    AssetRelation.target_asset_head_id == asset_head_id,
                )
            )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_lineage_graph(
        self, asset_head_id: uuid.UUID, max_depth: int = 2, direction: str = "both"
    ) -> LineageGraphRead:
        """Traverse relations using multi-hop BFS with cycle protection to produce lineage DAG."""
        root = await self.get_asset_head(asset_head_id)

        nodes: Dict[uuid.UUID, LineageNodeRead] = {}
        edges: Dict[uuid.UUID, LineageEdgeRead] = {}

        # Add root node
        nodes[root.id] = self._create_lineage_node(
            root, is_current=True, depth=0, direction="current"
        )

        direction_norm = direction.lower() if direction else "both"

        # Downstream traversal (outgoing: current -> target)
        if direction_norm in ("both", "downstream") and max_depth > 0:
            await self._traverse_bfs(
                start_id=root.id,
                max_depth=max_depth,
                is_downstream=True,
                nodes=nodes,
                edges=edges,
            )

        # Upstream traversal (incoming: source -> current)
        if direction_norm in ("both", "upstream") and max_depth > 0:
            await self._traverse_bfs(
                start_id=root.id,
                max_depth=max_depth,
                is_downstream=False,
                nodes=nodes,
                edges=edges,
            )

        return LineageGraphRead(
            root_asset_head_id=root.id,
            nodes=list(nodes.values()),
            edges=list(edges.values()),
        )

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    async def _validate_attributes_for_type(
        self, asset_type_id: uuid.UUID, attributes: Dict[str, Any]
    ) -> None:
        """Query metamodel attribute assignments and run dynamic schema validator."""
        stmt = (
            select(AssetTypeAttributeAssignment)
            .options(selectinload(AssetTypeAttributeAssignment.attribute_type))
            .where(AssetTypeAttributeAssignment.asset_type_id == asset_type_id)
        )
        result = await self.db.execute(stmt)
        assignments = list(result.scalars().all())
        if assignments:
            validate_asset_attributes(attributes, assignments)

    async def _traverse_bfs(
        self,
        start_id: uuid.UUID,
        max_depth: int,
        is_downstream: bool,
        nodes: Dict[uuid.UUID, LineageNodeRead],
        edges: Dict[uuid.UUID, LineageEdgeRead],
    ) -> None:
        """BFS multi-hop traversal with cycle detection."""
        queue: deque[Tuple[uuid.UUID, int]] = deque([(start_id, 0)])
        visited: Set[uuid.UUID] = {start_id}

        while queue:
            curr_id, curr_depth = queue.popleft()
            if curr_depth >= max_depth:
                continue

            rel_direction = "outgoing" if is_downstream else "incoming"
            relations = await self.list_relations(curr_id, direction=rel_direction)

            for rel in relations:
                next_id = rel.target_asset_head_id if is_downstream else rel.source_asset_head_id
                edges[rel.id] = LineageEdgeRead(
                    id=rel.id,
                    source_asset_head_id=rel.source_asset_head_id,
                    target_asset_head_id=rel.target_asset_head_id,
                    relation_type_id=rel.relation_type_id,
                    direction="downstream" if is_downstream else "upstream",
                )

                if next_id not in nodes:
                    try:
                        neighbor = await self.get_asset_head(next_id)
                        nodes[next_id] = self._create_lineage_node(
                            neighbor,
                            is_current=False,
                            depth=curr_depth + 1,
                            direction="downstream" if is_downstream else "upstream",
                        )
                    except EntityNotFoundException:
                        continue

                if next_id not in visited:
                    visited.add(next_id)
                    queue.append((next_id, curr_depth + 1))

    @staticmethod
    def _create_lineage_node(
        head: AssetHead, is_current: bool, depth: int, direction: str
    ) -> LineageNodeRead:
        """Construct LineageNodeRead from AssetHead."""
        active = head.published_version or head.active_draft_version
        return LineageNodeRead(
            id=head.id,
            name=active.name if active else "Untitled Asset",
            asset_type_id=head.asset_type_id,
            domain_id=head.domain_id,
            status=active.status.value if active else None,
            version_number=active.version_number if active else None,
            is_current=is_current,
            depth=depth,
            direction=direction,
        )
