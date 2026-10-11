"""Metamodel Dynamic Attribute Validator.

Validates asset attributes against metamodel attribute definitions.
Zero database, pure domain business logic.
"""
from datetime import date, datetime
import json
from typing import Any, Dict, List, Optional, Set

from app.domain.exceptions import ValidationException

# Normalized canonical data types
TYPE_MAP: Dict[str, str] = {
    "TEXT": "TEXT",
    "STRING": "TEXT",
    "MARKDOWN": "TEXT",
    "NUMBER": "NUMBER",
    "INT": "NUMBER",
    "INTEGER": "NUMBER",
    "FLOAT": "NUMBER",
    "BOOLEAN": "BOOLEAN",
    "BOOL": "BOOLEAN",
    "SINGLE_SELECT": "SINGLE_SELECT",
    "ENUM": "SINGLE_SELECT",
    "SELECT": "SINGLE_SELECT",
    "MULTI_SELECT": "MULTI_SELECT",
    "MULTISELECT": "MULTI_SELECT",
    "DATE": "DATE",
    "DATETIME": "DATE",
}


def _extract_allowed_values(raw: Any) -> Optional[List[Any]]:
    """Normalizes allowed_values into a flat list of primitive options."""
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return [raw]
    if isinstance(raw, (list, tuple, set)):
        result = []
        for item in raw:
            if hasattr(item, "value"):
                result.append(item.value)
            elif isinstance(item, dict) and "value" in item:
                result.append(item["value"])
            else:
                result.append(item)
        return result
    return None


def _parse_definition(defn: Any) -> Dict[str, Any]:
    """Extracts code, data_type, is_required, and allowed_values from dict or object."""
    if isinstance(defn, dict):
        if "attribute_type" in defn and isinstance(defn["attribute_type"], dict):
            attr_type = defn["attribute_type"]
            code = attr_type.get("code") or defn.get("code", "")
            data_type = attr_type.get("data_type") or defn.get("data_type", "TEXT")
            allowed_values = attr_type.get("allowed_values") or defn.get("allowed_values")
        elif hasattr(defn.get("attribute_type"), "code"):
            attr_type = defn["attribute_type"]
            code = getattr(attr_type, "code", "")
            data_type = getattr(attr_type, "data_type", "TEXT")
            allowed_values = getattr(attr_type, "allowed_values", None)
        else:
            code = defn.get("code", "")
            data_type = defn.get("data_type", "TEXT")
            allowed_values = defn.get("allowed_values")
        is_required = defn.get("is_required", False)
    else:
        # Object / SQLAlchemy model / Pydantic model
        if hasattr(defn, "attribute_type") and getattr(defn, "attribute_type") is not None:
            attr_type = getattr(defn, "attribute_type")
            code = getattr(attr_type, "code", "") or getattr(defn, "code", "")
            data_type = getattr(attr_type, "data_type", "TEXT") or getattr(defn, "data_type", "TEXT")
            allowed_values = getattr(attr_type, "allowed_values", None) or getattr(defn, "allowed_values", None)
        else:
            code = getattr(defn, "code", "")
            data_type = getattr(defn, "data_type", "TEXT")
            allowed_values = getattr(defn, "allowed_values", None)
        is_required = getattr(defn, "is_required", False)

    if hasattr(data_type, "value"):
        data_type = data_type.value
    raw_type_str = str(data_type).upper()
    canonical_type = TYPE_MAP.get(raw_type_str, raw_type_str)

    return {
        "code": str(code),
        "data_type": canonical_type,
        "is_required": bool(is_required),
        "allowed_values": _extract_allowed_values(allowed_values),
    }


def _is_valid_date(val: Any) -> bool:
    """Checks if value is a valid date or ISO 8601 date string."""
    if isinstance(val, (datetime, date)):
        return True
    if isinstance(val, str):
        try:
            date.fromisoformat(val)
            return True
        except ValueError:
            try:
                datetime.fromisoformat(val)
                return True
            except ValueError:
                return False
    return False


def validate_asset_attributes(
    attributes: Optional[Dict[str, Any]],
    attribute_definitions: Optional[List[Any]],
    raise_on_error: bool = False,
    raise_exception: bool = False,
) -> List[str]:
    """Validates asset attributes against metamodel attribute definitions.

    Args:
        attributes: Dictionary of attribute code to attribute value.
        attribute_definitions: List of attribute definitions or assignments.
        raise_on_error: If True, raises ValidationException if any errors occur.
        raise_exception: Alias for raise_on_error.

    Returns:
        List of validation error strings. Returns empty list if valid.

    Raises:
        ValidationException: When errors exist and raise_on_error or raise_exception is True.
    """
    errors: List[str] = []
    attrs = attributes or {}
    defs = attribute_definitions or []

    # If definitions is an object holding attribute_assignments (e.g. AssetType)
    if hasattr(defs, "attribute_assignments"):
        defs = getattr(defs, "attribute_assignments") or []

    for raw_defn in defs:
        defn = _parse_definition(raw_defn)
        code = defn["code"]
        if not code:
            continue

        data_type = defn["data_type"]
        is_required = defn["is_required"]
        allowed_values = defn["allowed_values"]

        val = attrs.get(code)

        # 1. Required constraint check
        if is_required:
            if code not in attrs or val is None:
                errors.append(f"Attribute '{code}' is required")
                continue
            if data_type == "TEXT" and isinstance(val, str) and not val.strip():
                errors.append(f"Attribute '{code}' cannot be empty")
                continue
            if data_type == "MULTI_SELECT" and isinstance(val, (list, tuple, set)) and len(val) == 0:
                errors.append(f"Attribute '{code}' cannot be empty")
                continue

        # If attribute is missing or None and not required, skip further type validation
        if val is None:
            continue

        # 2. Data type validation
        if data_type == "TEXT":
            if not isinstance(val, str):
                errors.append(f"Attribute '{code}' must be a string, got {type(val).__name__}")

        elif data_type == "NUMBER":
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                errors.append(f"Attribute '{code}' must be a number, got {type(val).__name__}")

        elif data_type == "BOOLEAN":
            if not isinstance(val, bool):
                errors.append(f"Attribute '{code}' must be a boolean, got {type(val).__name__}")

        elif data_type == "SINGLE_SELECT":
            if isinstance(val, (list, tuple, set, dict)):
                errors.append(f"Attribute '{code}' must be a single value, got {type(val).__name__}")
            elif allowed_values is not None:
                # Compare as strings or exact types
                val_str = str(val)
                allowed_strs = [str(opt) for opt in allowed_values]
                if val not in allowed_values and val_str not in allowed_strs:
                    errors.append(
                        f"Attribute '{code}' value '{val}' is not one of allowed values: {allowed_values}"
                    )

        elif data_type == "MULTI_SELECT":
            if not isinstance(val, (list, tuple, set)):
                errors.append(f"Attribute '{code}' must be a list of values, got {type(val).__name__}")
            elif allowed_values is not None:
                allowed_strs = [str(opt) for opt in allowed_values]
                for item in val:
                    item_str = str(item)
                    if item not in allowed_values and item_str not in allowed_strs:
                        errors.append(
                            f"Attribute '{code}' value '{item}' is not one of allowed values: {allowed_values}"
                        )

        elif data_type == "DATE":
            if not _is_valid_date(val):
                errors.append(
                    f"Attribute '{code}' must be a valid date (YYYY-MM-DD), got '{val}'"
                )

    if errors and (raise_on_error or raise_exception):
        raise ValidationException("; ".join(errors))

    return errors


def validate_or_raise(
    attributes: Optional[Dict[str, Any]],
    attribute_definitions: Optional[List[Any]],
) -> None:
    """Validates asset attributes and immediately raises ValidationException on error."""
    validate_asset_attributes(attributes, attribute_definitions, raise_on_error=True)
