"""Maintenance contracts for ORM model documentation."""

import ast
import unittest
from pathlib import Path


MODEL_DIR = Path(__file__).resolve().parents[1] / "model"


class ModelDocumentationTests(unittest.TestCase):
    """Require responsibility descriptions throughout the model package."""

    def test_modules_classes_functions_and_methods_have_docstrings(self):
        """Report every undocumented model symbol in one actionable failure."""
        undocumented = []

        for model_file in sorted(MODEL_DIR.glob("*.py")):
            module = ast.parse(
                model_file.read_text(encoding="utf-8"),
                filename=str(model_file),
            )
            if not ast.get_docstring(module):
                undocumented.append(model_file.name)

            for node in ast.walk(module):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not ast.get_docstring(node):
                        undocumented.append(f"{model_file.name}:{node.name}")

        self.assertEqual(undocumented, [])


if __name__ == "__main__":
    unittest.main()