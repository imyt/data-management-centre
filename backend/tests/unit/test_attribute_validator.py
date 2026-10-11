"""Pure unit tests for Metamodel Dynamic Attribute Validator.

Zero database, zero Docker, runs in milliseconds.
"""
from datetime import date, datetime
import pytest

from app.domain.exceptions import ValidationException
from app.domain.validation.attribute_validator import (
    validate_asset_attributes,
    validate_or_raise,
)
from app.models.metamodel import AttributeDataType


def test_text_attribute_validation():
    definitions = [
        {"code": "SUMMARY", "data_type": "TEXT", "is_required": True},
        {"code": "NOTES", "data_type": "STRING", "is_required": False},
        {"code": "DOCS", "data_type": "MARKDOWN", "is_required": False},
    ]

    # Valid text
    errors = validate_asset_attributes(
        {"SUMMARY": "Valid summary text", "NOTES": "Some notes", "DOCS": "# Markdown heading"},
        definitions,
    )
    assert errors == []

    # Non-string value for text
    errors = validate_asset_attributes(
        {"SUMMARY": 12345, "NOTES": True},
        definitions,
    )
    assert any("Attribute 'SUMMARY' must be a string" in e for e in errors)
    assert any("Attribute 'NOTES' must be a string" in e for e in errors)

    # Empty string for required attribute
    errors = validate_asset_attributes(
        {"SUMMARY": "   "},
        definitions,
    )
    assert any("Attribute 'SUMMARY' cannot be empty" in e for e in errors)

    # Empty string for optional attribute is valid
    errors = validate_asset_attributes(
        {"SUMMARY": "Valid text", "NOTES": ""},
        definitions,
    )
    assert errors == []


def test_number_attribute_validation():
    definitions = [
        {"code": "COUNT", "data_type": "NUMBER", "is_required": True},
        {"code": "SCORE", "data_type": "FLOAT", "is_required": False},
    ]

    # Valid integers and floats
    errors = validate_asset_attributes(
        {"COUNT": 42, "SCORE": 98.6},
        definitions,
    )
    assert errors == []

    # Boolean is rejected as number in Python
    errors = validate_asset_attributes(
        {"COUNT": True, "SCORE": False},
        definitions,
    )
    assert any("Attribute 'COUNT' must be a number" in e for e in errors)
    assert any("Attribute 'SCORE' must be a number" in e for e in errors)

    # String is rejected as number
    errors = validate_asset_attributes(
        {"COUNT": "42"},
        definitions,
    )
    assert any("Attribute 'COUNT' must be a number" in e for e in errors)


def test_boolean_attribute_validation():
    definitions = [
        {"code": "IS_ACTIVE", "data_type": "BOOLEAN", "is_required": True},
        {"code": "IS_DEPRECATED", "data_type": "BOOL", "is_required": False},
    ]

    # Valid booleans
    errors = validate_asset_attributes(
        {"IS_ACTIVE": True, "IS_DEPRECATED": False},
        definitions,
    )
    assert errors == []

    # Non-boolean values (numbers, strings) rejected
    errors = validate_asset_attributes(
        {"IS_ACTIVE": 1, "IS_DEPRECATED": "true"},
        definitions,
    )
    assert any("Attribute 'IS_ACTIVE' must be a boolean" in e for e in errors)
    assert any("Attribute 'IS_DEPRECATED' must be a boolean" in e for e in errors)


def test_single_select_attribute_validation():
    definitions = [
        {
            "code": "CONFIDENTIALITY",
            "data_type": "SINGLE_SELECT",
            "allowed_values": ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"],
            "is_required": True,
        },
        {
            "code": "TIER",
            "data_type": "ENUM",
            "allowed_values": ["GOLD", "SILVER", "BRONZE"],
            "is_required": False,
        },
    ]

    # Valid selections
    errors = validate_asset_attributes(
        {"CONFIDENTIALITY": "INTERNAL", "TIER": "GOLD"},
        definitions,
    )
    assert errors == []

    # Invalid selection
    errors = validate_asset_attributes(
        {"CONFIDENTIALITY": "SUPER_SECRET", "TIER": "PLATINUM"},
        definitions,
    )
    assert any("Attribute 'CONFIDENTIALITY' value 'SUPER_SECRET' is not one of allowed values" in e for e in errors)
    assert any("Attribute 'TIER' value 'PLATINUM' is not one of allowed values" in e for e in errors)

    # Passing a list to single select is rejected
    errors = validate_asset_attributes(
        {"CONFIDENTIALITY": ["INTERNAL"]},
        definitions,
    )
    assert any("Attribute 'CONFIDENTIALITY' must be a single value" in e for e in errors)


def test_multi_select_attribute_validation():
    definitions = [
        {
            "code": "TAGS",
            "data_type": "MULTI_SELECT",
            "allowed_values": ["PII", "FINANCIAL", "GDPR", "HIPAA", "SOX"],
            "is_required": True,
        },
        {
            "code": "SECONDARY_TAGS",
            "data_type": "MULTISELECT",
            "allowed_values": ["ANALYTICS", "ML", "REPORTING"],
            "is_required": False,
        },
    ]

    # Valid multi selections
    errors = validate_asset_attributes(
        {"TAGS": ["PII", "GDPR"], "SECONDARY_TAGS": ["ML"]},
        definitions,
    )
    assert errors == []

    # Invalid option in list
    errors = validate_asset_attributes(
        {"TAGS": ["PII", "UNKNOWN_TAG"]},
        definitions,
    )
    assert any("Attribute 'TAGS' value 'UNKNOWN_TAG' is not one of allowed values" in e for e in errors)

    # Passing a scalar string to multi select is rejected
    errors = validate_asset_attributes(
        {"TAGS": "PII"},
        definitions,
    )
    assert any("Attribute 'TAGS' must be a list of values" in e for e in errors)

    # Empty list for required multi-select is rejected
    errors = validate_asset_attributes(
        {"TAGS": []},
        definitions,
    )
    assert any("Attribute 'TAGS' cannot be empty" in e for e in errors)


def test_date_attribute_validation():
    definitions = [
        {"code": "EXPIRY_DATE", "data_type": "DATE", "is_required": True},
        {"code": "REVIEW_DATE", "data_type": "DATETIME", "is_required": False},
    ]

    # Valid ISO date strings
    errors = validate_asset_attributes(
        {"EXPIRY_DATE": "2026-12-31", "REVIEW_DATE": "2026-10-15"},
        definitions,
    )
    assert errors == []

    # Valid date/datetime objects
    errors = validate_asset_attributes(
        {"EXPIRY_DATE": date(2026, 12, 31), "REVIEW_DATE": datetime(2026, 10, 15, 12, 0, 0)},
        definitions,
    )
    assert errors == []

    # Invalid date strings
    errors = validate_asset_attributes(
        {"EXPIRY_DATE": "not-a-date", "REVIEW_DATE": "2026-13-45"},
        definitions,
    )
    assert any("Attribute 'EXPIRY_DATE' must be a valid date" in e for e in errors)
    assert any("Attribute 'REVIEW_DATE' must be a valid date" in e for e in errors)

    # Invalid type
    errors = validate_asset_attributes(
        {"EXPIRY_DATE": 20261231},
        definitions,
    )
    assert any("Attribute 'EXPIRY_DATE' must be a valid date" in e for e in errors)


def test_required_and_optional_constraints():
    definitions = [
        {"code": "REQ_ATTR", "data_type": "TEXT", "is_required": True},
        {"code": "OPT_ATTR", "data_type": "TEXT", "is_required": False},
    ]

    # Missing required attribute
    errors = validate_asset_attributes({}, definitions)
    assert any("Attribute 'REQ_ATTR' is required" in e for e in errors)

    # None for required attribute
    errors = validate_asset_attributes({"REQ_ATTR": None}, definitions)
    assert any("Attribute 'REQ_ATTR' is required" in e for e in errors)

    # None for optional attribute is valid
    errors = validate_asset_attributes({"REQ_ATTR": "present", "OPT_ATTR": None}, definitions)
    assert errors == []


def test_raises_validation_exception():
    definitions = [
        {"code": "CRITICALITY", "data_type": "SINGLE_SELECT", "allowed_values": ["HIGH", "LOW"], "is_required": True}
    ]

    # Normal returns list
    errors = validate_asset_attributes({"CRITICALITY": "INVALID"}, definitions)
    assert len(errors) == 1

    # raise_on_error=True raises ValidationException
    with pytest.raises(ValidationException, match="CRITICALITY"):
        validate_asset_attributes({"CRITICALITY": "INVALID"}, definitions, raise_on_error=True)

    # validate_or_raise raises ValidationException
    with pytest.raises(ValidationException, match="CRITICALITY"):
        validate_or_raise({"CRITICALITY": "INVALID"}, definitions)

    # Valid attributes does not raise
    validate_or_raise({"CRITICALITY": "HIGH"}, definitions)


def test_nested_and_object_attribute_definitions():
    # Nested dictionary format as returned by AssetTypeAttributeAssignment
    nested_definitions = [
        {
            "is_required": True,
            "attribute_type": {
                "code": "OWNER",
                "data_type": AttributeDataType.STRING,
                "allowed_values": None,
            },
        },
        {
            "is_required": False,
            "attribute_type": {
                "code": "STATUS",
                "data_type": AttributeDataType.ENUM,
                "allowed_values": [{"value": "OPEN", "label": "Open"}, {"value": "CLOSED", "label": "Closed"}],
            },
        },
    ]

    errors = validate_asset_attributes({"OWNER": "Engineering", "STATUS": "OPEN"}, nested_definitions)
    assert errors == []

    errors = validate_asset_attributes({"OWNER": "", "STATUS": "PENDING"}, nested_definitions)
    assert any("Attribute 'OWNER' cannot be empty" in e for e in errors)
    assert any("Attribute 'STATUS' value 'PENDING' is not one of allowed values" in e for e in errors)


def test_attribute_validation_integration():
    definitions = [
        {"code": "TIER", "data_type": "SINGLE_SELECT", "allowed_values": ["GOLD", "SILVER"], "is_required": True},
        {"code": "RETENTION_YEARS", "data_type": "NUMBER", "is_required": False},
    ]

    # Fails validation
    errors = validate_asset_attributes({"TIER": "BRONZE"}, definitions)
    assert any("TIER" in e for e in errors)

    # Valid attributes
    errors = validate_asset_attributes({"TIER": "GOLD", "RETENTION_YEARS": 5}, definitions)
    assert len(errors) == 0

    # Invalid number
    errors = validate_asset_attributes({"TIER": "GOLD", "RETENTION_YEARS": "not_a_number"}, definitions)
    assert any("RETENTION_YEARS" in e for e in errors)

