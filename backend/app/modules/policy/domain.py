"""Rule types, selectors and the sentences that explain them. Pure: no database.

A selector is `{"subject": "asset", "where": {"is_stored": true, "data_category.in": [..]}}`.
Every key in `where` is an attribute of the subject type, optionally with an operator suffix
(`.in`, `.not_in`); all conditions must hold. There is no way to name one application or asset.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.core.errors import InvalidInputError
from app.modules.inventory.service import AttributeSpec, AttributeValue, SubjectType


def check_in(column: str, values: type[StrEnum]) -> str:
    """SQL for a check constraint that keeps `column` within an enum's values."""
    quoted = ", ".join(f"'{v.value}'" for v in values)
    return f"{column} IN ({quoted})"


class ControlStatus(StrEnum):
    ACTIVE = "active"
    RETIRED = "retired"


class AppliedControlStatus(StrEnum):
    """An applied control is never deleted: it stays `retired` so its history remains."""

    ACTIVE = "active"
    RETIRED = "retired"


# --- Rule types ------------------------------------------------------------------------------


@dataclass(frozen=True)
class ParamSpec:
    name: str
    label: str
    kind: str  # "integer" or "choices"
    default: int | list[str]
    minimum: int = 0
    choices: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuleType:
    """A kind of check. The evaluator for it arrives with the evaluation engine (slice 6); policy
    only needs to know what it applies to and which parameters it takes."""

    key: str
    label: str
    description: str
    subjects: tuple[SubjectType, ...]
    params: tuple[ParamSpec, ...] = ()


RULE_TYPES: dict[str, RuleType] = {
    t.key: t
    for t in (
        RuleType(
            key="retention_window",
            label="Retention window",
            description="The oldest record is within the retention policy of the asset.",
            subjects=(SubjectType.ASSET,),
            params=(
                ParamSpec("grace_days", "Grace period (days)", "integer", default=0, minimum=0),
            ),
        ),
        RuleType(
            key="harvest_fresh",
            label="Harvest is fresh",
            description="The data store has been harvested successfully within its window.",
            subjects=(SubjectType.DATA_STORE,),
            params=(
                ParamSpec(
                    "max_age_hours",
                    "Longest time since a harvest (hours)",
                    "integer",
                    default=48,
                    minimum=1,
                ),
            ),
        ),
        RuleType(
            key="declaration_complete",
            label="Declarations complete",
            description="The required declarations exist for the asset or application.",
            subjects=(SubjectType.ASSET, SubjectType.APPLICATION),
            params=(
                ParamSpec(
                    "required_fields",
                    "Required declarations",
                    "choices",
                    default=["owner"],
                    choices=(
                        "data_category",
                        "business_context",
                        "owner",
                        "steward",
                        "description",
                        "app_owner",
                        "tech_owner",
                    ),
                ),
            ),
        ),
    )
}


def rule_type(key: str) -> RuleType:
    found = RULE_TYPES.get(key)
    if found is None:
        raise InvalidInputError(
            f"{key!r} is not a rule type.",
            details={"field": "rule_type", "known": list(RULE_TYPES)},
        )
    return found


def validate_params(rule: RuleType, params: dict[str, Any]) -> dict[str, Any]:
    """The params with defaults filled in. Unknown or malformed params are refused."""
    known = {p.name: p for p in rule.params}
    unknown = sorted(set(params) - set(known))
    if unknown:
        raise InvalidInputError(
            f"{rule.label} has no parameter {unknown[0]!r}.",
            details={"field": "params", "unknown": unknown},
        )
    result: dict[str, Any] = {}
    for spec in rule.params:
        value = params.get(spec.name, spec.default)
        if spec.kind == "integer":
            if isinstance(value, bool) or not isinstance(value, int) or value < spec.minimum:
                raise InvalidInputError(
                    f"{spec.label} must be a whole number of at least {spec.minimum}.",
                    details={"field": "params", "param": spec.name},
                )
        else:
            if (
                not isinstance(value, list)
                or not value
                or any(v not in spec.choices for v in value)
            ):
                raise InvalidInputError(
                    f"{spec.label} must be a non-empty list of: {', '.join(spec.choices)}.",
                    details={"field": "params", "param": spec.name},
                )
            value = sorted(set(value))
        result[spec.name] = value
    return result


# --- Selectors -------------------------------------------------------------------------------


class Operator(StrEnum):
    EQUALS = "equals"
    IN = "in"
    NOT_IN = "not_in"


_SUFFIXES = {".in": Operator.IN, ".not_in": Operator.NOT_IN}


@dataclass(frozen=True)
class Condition:
    attribute: str
    operator: Operator
    values: tuple[AttributeValue, ...]  # one value for `equals`


@dataclass(frozen=True)
class Selector:
    subject: SubjectType
    conditions: tuple[Condition, ...]

    def to_json(self) -> dict[str, Any]:
        where: dict[str, Any] = {}
        for c in self.conditions:
            if c.operator is Operator.EQUALS:
                where[c.attribute] = c.values[0]
            else:
                suffix = ".in" if c.operator is Operator.IN else ".not_in"
                where[c.attribute + suffix] = list(c.values)
        return {"subject": self.subject.value, "where": where}


def parse_selector(
    raw: dict[str, Any], vocabulary: dict[SubjectType, dict[str, AttributeSpec]]
) -> Selector:
    """Check a selector against the attributes of its subject type. Refuses anything else."""
    subject_raw = raw.get("subject")
    where = raw.get("where", {})
    extra = sorted(set(raw) - {"subject", "where"})
    if extra or not isinstance(where, dict):
        raise InvalidInputError(
            "A selector has a `subject` and a `where` object.", details={"field": "selector"}
        )
    try:
        subject = SubjectType(str(subject_raw))
    except ValueError:
        raise InvalidInputError(
            f"{subject_raw!r} is not a subject type.", details={"field": "selector.subject"}
        ) from None
    attributes = vocabulary[subject]
    conditions = []
    for key, value in where.items():
        name, operator = key, Operator.EQUALS
        for suffix, candidate in _SUFFIXES.items():
            if key.endswith(suffix):
                name, operator = key[: -len(suffix)], candidate
        spec = attributes.get(name)
        if spec is None:
            raise InvalidInputError(
                f"{name!r} is not an attribute of {subject.value.replace('_', ' ')}s. "
                "Selectors use attributes, never names.",
                details={"field": "selector.where", "attribute": name},
            )
        values = _values(spec, operator, value)
        conditions.append(Condition(name, operator, values))
    return Selector(subject, tuple(sorted(conditions, key=lambda c: (c.attribute, c.operator))))


def _values(spec: AttributeSpec, operator: Operator, value: Any) -> tuple[AttributeValue, ...]:
    if spec.kind == "boolean":
        if operator is not Operator.EQUALS or not isinstance(value, bool):
            raise InvalidInputError(
                f"{spec.label} is yes or no.", details={"field": "selector.where"}
            )
        return (value,)
    raw = [value] if operator is Operator.EQUALS else value
    allowed = {o.value for o in spec.options}
    if (
        not isinstance(raw, list)
        or not raw
        or any(not isinstance(v, str) or v not in allowed for v in raw)
    ):
        raise InvalidInputError(
            f"{spec.label} must be {'one of ' if operator is not Operator.EQUALS else ''}"
            f"{', '.join(sorted(allowed))}.",
            details={"field": "selector.where", "attribute": spec.name},
        )
    return tuple(sorted(set(raw)))


def selector_from_stored(raw: dict[str, Any]) -> Selector:
    """A selector already validated when its rule version was published."""
    conditions = []
    for key, value in raw["where"].items():
        name, operator = key, Operator.EQUALS
        for suffix, candidate in _SUFFIXES.items():
            if key.endswith(suffix):
                name, operator = key[: -len(suffix)], candidate
        values = tuple(value) if isinstance(value, list) else (value,)
        conditions.append(Condition(name, operator, values))
    return Selector(
        SubjectType(raw["subject"]),
        tuple(sorted(conditions, key=lambda c: (c.attribute, c.operator))),
    )


def holds(condition: Condition, attributes: dict[str, AttributeValue]) -> bool:
    actual = attributes.get(condition.attribute)
    if condition.operator is Operator.EQUALS:
        return actual == condition.values[0]
    if condition.operator is Operator.IN:
        return actual is not None and actual in condition.values
    return actual is None or actual not in condition.values


def matches(selector: Selector, attributes: dict[str, AttributeValue]) -> bool:
    return all(holds(c, attributes) for c in selector.conditions)


# --- Reasons ---------------------------------------------------------------------------------


def _list(spec: AttributeSpec, values: tuple[AttributeValue, ...]) -> str:
    return ", ".join(spec.label_for(v) for v in values)


def describe(condition: Condition, spec: AttributeSpec) -> str:
    """The condition as a phrase: `Data category is one of Personal, Payment`."""
    if condition.operator is Operator.EQUALS:
        return f"{spec.label} is {spec.label_for(condition.values[0])}"
    if condition.operator is Operator.IN:
        return f"{spec.label} is one of {_list(spec, condition.values)}"
    return f"{spec.label} is none of {_list(spec, condition.values)}"


def _actual(spec: AttributeSpec, attributes: dict[str, AttributeValue]) -> str:
    value = attributes.get(spec.name)
    return "not set" if value is None else spec.label_for(value)


def _applies(
    condition: Condition, spec: AttributeSpec, attributes: dict[str, AttributeValue]
) -> str:
    phrase = describe(condition, spec)
    if condition.operator is Operator.EQUALS:
        return phrase
    return f"{phrase} (it is {_actual(spec, attributes)})"


def why_applies(
    selector: Selector, attributes: dict[str, AttributeValue], specs: dict[str, AttributeSpec]
) -> str:
    """Why a subject has the control: each condition and the value that satisfies it."""
    if not selector.conditions:
        return f"Applies to every {selector.subject.value.replace('_', ' ')}."
    parts = [_applies(c, specs[c.attribute], attributes) for c in selector.conditions]
    return "Applies because " + "; ".join(parts) + "."


def why_not(
    selector: Selector, attributes: dict[str, AttributeValue], specs: dict[str, AttributeSpec]
) -> str:
    """Why a subject no longer has the control: the conditions that stopped holding."""
    failing = [
        f"{describe(c, specs[c.attribute])} is required but it is "
        f"{_actual(specs[c.attribute], attributes)}"
        for c in selector.conditions
        if not holds(c, attributes)
    ]
    return "No longer applies: " + "; ".join(failing) + "."


def matched_values(
    selector: Selector, attributes: dict[str, AttributeValue]
) -> dict[str, AttributeValue | None]:
    """The values of the attributes the selector read, recorded with the applied control."""
    return {c.attribute: attributes.get(c.attribute) for c in selector.conditions}
