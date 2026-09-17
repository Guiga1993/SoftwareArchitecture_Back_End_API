import unittest

from pydantic import ValidationError

from schemas.hydrogen_generator import HydrogenGeneratorCreateSchema


def generator_data(**overrides):
    data = {
        "serial_number": "GEN-0001",
        "acquisition_type": "Leasing",
        "stack_type": "PEMFC",
        "number_of_cells": 10,
        "stack_voltage": 12.5,
        "current_density": 0.5,
        "length_in": 24,
        "width_in": 16,
        "height_in": 12,
        "weight_lb": 50,
    }
    data.update(overrides)
    return data


class HydrogenGeneratorCreateSchemaTests(unittest.TestCase):
    def test_accepts_standard_parcel_measurements(self):
        schema = HydrogenGeneratorCreateSchema(**generator_data())

        self.assertEqual(schema.length_in, 24)
        self.assertEqual(schema.weight_lb, 50)

    def test_rejects_weight_above_150_lb(self):
        with self.assertRaisesRegex(ValidationError, "less than or equal to 150"):
            HydrogenGeneratorCreateSchema(**generator_data(weight_lb=151))

    def test_rejects_length_plus_girth_above_165_in(self):
        with self.assertRaisesRegex(ValidationError, "length-plus-girth limit"):
            HydrogenGeneratorCreateSchema(
                **generator_data(length_in=60, width_in=30, height_in=25)
            )


if __name__ == "__main__":
    unittest.main()