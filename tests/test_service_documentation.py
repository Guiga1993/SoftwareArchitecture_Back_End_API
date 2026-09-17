"""Maintenance contracts for service-layer documentation."""

import ast
import unittest
from pathlib import Path


SERVICES_DIR = Path(__file__).resolve().parents[1] / "services"


class ServiceDocumentationTests(unittest.TestCase):
    """Require responsibility descriptions throughout production services."""

    def test_modules_classes_functions_and_methods_have_docstrings(self):
        """Report every undocumented service symbol in one actionable failure."""
        undocumented = []

        for service_file in sorted(SERVICES_DIR.glob("*.py")):
            module = ast.parse(
                service_file.read_text(encoding="utf-8"),
                filename=str(service_file),
            )
            if not ast.get_docstring(module):
                undocumented.append(service_file.name)

            for node in ast.walk(module):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not ast.get_docstring(node):
                        undocumented.append(f"{service_file.name}:{node.name}")

        self.assertEqual(undocumented, [])


if __name__ == "__main__":
    unittest.main()