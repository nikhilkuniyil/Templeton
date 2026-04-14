"""Small JSON-schema-like validator for local runtime checks."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from .schemas import load_schema


class ValidationError(ValueError):
    """Raised when data does not satisfy a schema."""


class SchemaValidator:
    """Validates a limited subset of JSON Schema used by this project."""

    def validate(self, schema_name: str, data: Any) -> None:
        schema = load_schema(schema_name)
        normalized = self._normalize(data)
        self._validate_schema(schema=schema, data=normalized, path=schema_name)

    def _normalize(self, data: Any) -> Any:
        if is_dataclass(data):
            return asdict(data)
        return data

    def _validate_schema(self, schema: dict[str, Any], data: Any, path: str) -> None:
        if "const" in schema and data != schema["const"]:
            raise ValidationError(f"{path}: expected constant {schema['const']!r}, got {data!r}")

        if "enum" in schema and data not in schema["enum"]:
            raise ValidationError(f"{path}: expected one of {schema['enum']!r}, got {data!r}")

        schema_type = schema.get("type")
        if schema_type is not None:
            self._validate_type(schema_type=schema_type, data=data, path=path)

        if schema.get("type") == "object" or (
            isinstance(schema.get("type"), list) and "object" in schema["type"] and isinstance(data, dict)
        ):
            self._validate_object(schema=schema, data=data, path=path)
        elif schema.get("type") == "array" or (
            isinstance(schema.get("type"), list) and "array" in schema["type"] and isinstance(data, list)
        ):
            self._validate_array(schema=schema, data=data, path=path)

    def _validate_type(self, schema_type: str | list[str], data: Any, path: str) -> None:
        allowed_types = schema_type if isinstance(schema_type, list) else [schema_type]
        for allowed_type in allowed_types:
            if self._matches_type(allowed_type, data):
                return
        raise ValidationError(f"{path}: expected type {allowed_types!r}, got {type(data).__name__}")

    def _matches_type(self, allowed_type: str, data: Any) -> bool:
        if allowed_type == "null":
            return data is None
        if allowed_type == "object":
            return isinstance(data, dict)
        if allowed_type == "array":
            return isinstance(data, list)
        if allowed_type == "string":
            return isinstance(data, str)
        if allowed_type == "boolean":
            return isinstance(data, bool)
        if allowed_type == "number":
            return isinstance(data, (int, float)) and not isinstance(data, bool)
        return True

    def _validate_object(self, schema: dict[str, Any], data: Any, path: str) -> None:
        if not isinstance(data, dict):
            raise ValidationError(f"{path}: expected object, got {type(data).__name__}")

        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for name in required:
            if name not in data:
                raise ValidationError(f"{path}: missing required property {name!r}")

        if schema.get("additionalProperties") is False:
            unknown_keys = set(data) - set(properties)
            if unknown_keys:
                raise ValidationError(f"{path}: unknown properties {sorted(unknown_keys)!r}")

        for key, value in data.items():
            if key in properties:
                self._validate_schema(properties[key], value, f"{path}.{key}")

    def _validate_array(self, schema: dict[str, Any], data: Any, path: str) -> None:
        if not isinstance(data, list):
            raise ValidationError(f"{path}: expected array, got {type(data).__name__}")
        item_schema = schema.get("items")
        if item_schema is None:
            return
        for index, item in enumerate(data):
            self._validate_schema(item_schema, item, f"{path}[{index}]")
