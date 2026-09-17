from io import StringIO

import pytest
from django.core.management import call_command


@pytest.mark.unit
def test_openapi_schema_generation_has_no_introspection_diagnostics(tmp_path):
    stderr = StringIO()
    schema_path = tmp_path / "schema.yaml"

    call_command(
        "spectacular",
        validate=True,
        file=str(schema_path),
        stderr=stderr,
    )

    assert schema_path.is_file()
    assert stderr.getvalue() == ""
