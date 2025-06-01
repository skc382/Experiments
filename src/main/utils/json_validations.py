from enum import Enum
from jsonschema import validate, ValidationError
from pydantic import BaseModel, ValidationError as PydanticValidationError
from typing import Tuple, Union


# Enum for schema identification
class SchemaNamespace(Enum):
    SCHEMA_ONE = "schemaOne"
    SCHEMA_TWO = "schemaTwo"


# Define JSON Schema for validation
schemaOne = {
    "type": "object",
    "properties": {
        "prompt": {"type": "string"}
    },
    "required": ["prompt"]
}

schemaTwo = {
    "type": "object",
    "properties": {
        "image_data": {"type": "string"},
        "prompt": {"type": "string"}
    },
    "required": ["image_data", "prompt"]
}


# Define typed Python data models for each schema
class SchemaOneModel(BaseModel):
    prompt: str = ""  # optional in schema, defaults to empty string


class SchemaTwoModel(BaseModel):
    image_data: str
    prompt: str = ""


def validate_and_load(json_data: dict) -> Tuple[SchemaNamespace, Union[SchemaOneModel, SchemaTwoModel]]:
    """
    Validates input JSON against known schemas and loads into the appropriate model.

    :param json_data: dict - input JSON to validate
    :return: (SchemaNamespace, LoadedModelInstance)
    :raises ValueError: if JSON doesn't match any schema
    """
    try:
        validate(instance=json_data, schema=schemaTwo)
        model = SchemaTwoModel(**json_data)
        return SchemaNamespace.SCHEMA_TWO, model
    except (ValidationError, PydanticValidationError) as e2:
        error_two = str(e2)

    try:
        validate(instance=json_data, schema=schemaOne)
        model = SchemaOneModel(**json_data)
        return SchemaNamespace.SCHEMA_ONE, model
    except (ValidationError, PydanticValidationError) as e1:
        error_one = str(e1)

    raise ValueError(
        f"Input JSON does not match any known schema.\n\n"
        f"- SchemaOne error: {error_one}\n\n"
        f"- SchemaTwo error: {error_two}"
    )


# Example usage
if __name__ == "__main__":
    input_json = {
        "image_data": "base64string==",
        "prompt": "Generate a landscape"
    }

    try:
        schema_ns, loaded_obj = validate_and_load(input_json)
        print(f"Matched: {schema_ns.value}")
        print(f"Parsed Object: {loaded_obj}")
    except ValueError as err:
        print("Validation failed:")
        print(err)
