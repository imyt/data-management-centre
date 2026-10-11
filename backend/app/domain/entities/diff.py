"""Domain calculations for semantic visual diffing and change detection."""
import difflib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MarkdownDiffResult:
    has_changes: bool
    old_text: str
    new_text: str
    unified_diff: List[str]


@dataclass
class AttributeDiffItem:
    attribute_code: str
    old_value: Any
    new_value: Any
    change_type: str  # ADDED, MODIFIED, REMOVED, UNCHANGED


@dataclass
class RelationsDiffResult:
    added: List[Dict[str, Any]]
    removed: List[Dict[str, Any]]
    unchanged: List[Dict[str, Any]]
    total_changes: int


@dataclass
class VisualDiffResult:
    has_changes: bool
    name_diff: Dict[str, Any]
    description_diff: Dict[str, Any]
    attributes_diff: List[Dict[str, Any]]
    relations_diff: Dict[str, Any]


def compute_markdown_diff(old_text: Optional[str], new_text: Optional[str]) -> Dict[str, Any]:
    """Generates structured unified line-by-line diff for markdown descriptions."""
    old_lines = (old_text or "").splitlines(keepends=True)
    new_lines = (new_text or "").splitlines(keepends=True)
    
    diff = list(difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile="Published",
        tofile="Draft",
        lineterm=""
    ))
    
    return {
        "has_changes": (old_text or "") != (new_text or ""),
        "old_text": old_text or "",
        "new_text": new_text or "",
        "unified_diff": diff,
    }


def compute_attributes_diff(
    old_payload: Dict[str, Any],
    new_payload: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Calculates attribute-by-attribute mutations showing added, modified, removed, or unchanged values."""
    all_keys = sorted(set(old_payload.keys()) | set(new_payload.keys()))
    diff_results = []
    
    for key in all_keys:
        old_val = old_payload.get(key)
        new_val = new_payload.get(key)
        
        if key not in old_payload:
            change_type = "ADDED"
        elif key not in new_payload:
            change_type = "REMOVED"
        elif old_val != new_val:
            change_type = "MODIFIED"
        else:
            change_type = "UNCHANGED"
            
        diff_results.append({
            "attribute_code": key,
            "old_value": old_val,
            "new_value": new_val,
            "change_type": change_type
        })
        
    return diff_results


def compute_relations_diff(
    old_relations: List[Dict[str, Any]],
    new_relations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Detects added or removed relation links between two versions."""
    old_signatures = {f"{r.get('relation_type_code')}:{r.get('target_asset_id')}": r for r in old_relations}
    new_signatures = {f"{r.get('relation_type_code')}:{r.get('target_asset_id')}": r for r in new_relations}

    added = [r for sig, r in new_signatures.items() if sig not in old_signatures]
    removed = [r for sig, r in old_signatures.items() if sig not in new_signatures]
    unchanged = [r for sig, r in new_signatures.items() if sig in old_signatures]

    return {
        "added": added,
        "removed": removed,
        "unchanged": unchanged,
        "total_changes": len(added) + len(removed)
    }


def generate_version_diff(
    published_version: Optional[Any],
    draft_version: Any
) -> VisualDiffResult:
    """Generates complete side-by-side visual diff between published and draft states."""
    old_name = published_version.name if published_version else ""
    old_desc = published_version.description_markdown if published_version else ""
    old_attrs = published_version.attributes_payload if published_version else {}
    old_rels = published_version.relations_snapshot if published_version else []

    name_changed = old_name != draft_version.name
    markdown_diff = compute_markdown_diff(old_desc, draft_version.description_markdown)
    attributes_diff = compute_attributes_diff(old_attrs, draft_version.attributes_payload)
    relations_diff = compute_relations_diff(old_rels, draft_version.relations_snapshot)

    has_changes = (
        name_changed or
        markdown_diff["has_changes"] or
        any(a["change_type"] != "UNCHANGED" for a in attributes_diff) or
        relations_diff["total_changes"] > 0
    )

    return VisualDiffResult(
        has_changes=has_changes,
        name_diff={
            "old_name": old_name,
            "new_name": draft_version.name,
            "changed": name_changed,
        },
        description_diff=markdown_diff,
        attributes_diff=attributes_diff,
        relations_diff=relations_diff,
    )
