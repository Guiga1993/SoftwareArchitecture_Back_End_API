"""Maintenance contracts for API schema documentation."""

import ast
import unittest
from pathlib import Path


SCHEMAS_DIR = Path(__file__).resolve().parents[1] / "schemas"


class SchemaDocumentationTests(unittest.TestCase):
    """Require responsibility descriptions throughout the schemas package."""

    def test_modules_classes_functions_and_methods_have_docstrings(self):
        """Report every undocumented schema symbol in one actionable failure."""
        undocumented = []

        for schema_file in sorted(SCHEMAS_DIR.glob("*.py")):
            module = ast.parse(
                schema_file.read_text(encoding="utf-8"),
                filename=str(schema_file),
            )
            if not ast.get_docstring(module):
                undocumented.append(schema_file.name)

            for node in ast.walk(module):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not ast.get_docstring(node):
                        undocumented.append(f"{schema_file.name}:{node.name}")

        self.assertEqual(undocumented, [])


if __name__ == "__main__":
    unittest.main()