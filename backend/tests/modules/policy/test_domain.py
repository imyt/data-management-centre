import pytest

from app.core.errors import InvalidInputError
from app.modules.inventory.service import AttributeSpec, SubjectType, ValueOption
from app.modules.policy.domain import (
    RULE_TYPES,
    matches,
    parse_selector,
    selector_from_stored,
    validate_params,
    why_applies,
    why_not,
)

SPECS = {
    SubjectType.ASSET: {
        "is_stored": AttributeSpec("is_stored", "Stored", "boolean"),
        "data_category": AttributeSpec(
            "data_category",
            "Data category",
            "choice",
            (
                ValueOption("personal", "Personal"),
                ValueOption("payment", "Payment"),
                ValueOption("internal", "Internal"),
            ),
        ),
    },
    SubjectType.DATA_STORE: {},
    SubjectType.APPLICATION: {},
}


def _selector(where: dict) -> object:
    return parse_selector({"subject": "asset", "where": where}, SPECS)


def test_a_selector_reads_attributes_and_all_conditions_must_hold() -> None:
    selector = _selector({"is_stored": True, "data_category.in": ["personal", "payment"]})

    assert matches(selector, {"is_stored": True, "data_category": "payment"})
    assert not matches(selector, {"is_stored": False, "data_category": "payment"})
    assert not matches(selector, {"is_stored": True, "data_category": "internal"})
    assert not matches(selector, {"is_stored": True})  # no category: `in` cannot hold


def test_not_in_holds_when_the_attribute_is_missing() -> None:
    selector = _selector({"data_category.not_in": ["personal"]})

    assert matches(selector, {})
    assert matches(selector, {"data_category": "internal"})
    assert not matches(selector, {"data_category": "personal"})


def test_an_empty_selector_matches_every_subject_of_its_type() -> None:
    assert matches(_selector({}), {"is_stored": False})


def test_the_stored_form_round_trips() -> None:
    selector = _selector({"data_category.in": ["payment", "personal"], "is_stored": True})

    assert selector_from_stored(selector.to_json()) == selector


@pytest.mark.parametrize(
    "where",
    [
        {"name": "Customer master"},  # a name is not an attribute: selectors never name things
        {"id": "0199f000-0000-7000-8000-000000000001"},
        {"is_stored": "yes"},
        {"is_stored.in": [True]},
        {"data_category": "secret"},
        {"data_category.in": []},
        {"data_category.in": "personal"},
    ],
)
def test_a_selector_that_names_things_or_uses_a_wrong_value_is_refused(where: dict) -> None:
    with pytest.raises(InvalidInputError):
        _selector(where)


def test_a_selector_needs_a_known_subject_and_no_extra_keys() -> None:
    with pytest.raises(InvalidInputError):
        parse_selector({"subject": "table", "where": {}}, SPECS)
    with pytest.raises(InvalidInputError):
        parse_selector({"subject": "asset", "where": {}, "name": "x"}, SPECS)


def test_reasons_say_what_held_and_what_stopped_holding() -> None:
    specs = SPECS[SubjectType.ASSET]
    selector = _selector({"is_stored": True, "data_category.in": ["personal", "payment"]})

    assert why_applies(selector, {"is_stored": True, "data_category": "payment"}, specs) == (
        "Applies because Data category is one of Payment, Personal (it is Payment); Stored is yes."
    )
    assert why_not(selector, {"is_stored": True, "data_category": "internal"}, specs) == (
        "No longer applies: Data category is one of Payment, Personal is required but it is "
        "Internal."
    )


def test_params_get_their_defaults_and_bad_ones_are_refused() -> None:
    rule = RULE_TYPES["harvest_fresh"]

    assert validate_params(rule, {}) == {"max_age_hours": 48}
    assert validate_params(rule, {"max_age_hours": 6}) == {"max_age_hours": 6}
    for bad in ({"max_age_hours": 0}, {"max_age_hours": "6"}, {"max_age_hours": True}, {"x": 1}):
        with pytest.raises(InvalidInputError):
            validate_params(rule, bad)


def test_choice_params_are_checked_against_their_choices() -> None:
    rule = RULE_TYPES["declaration_complete"]

    assert validate_params(rule, {"required_fields": ["owner", "owner", "steward"]}) == {
        "required_fields": ["owner", "steward"]
    }
    for bad in ({"required_fields": []}, {"required_fields": ["colour"]}):
        with pytest.raises(InvalidInputError):
            validate_params(rule, bad)
