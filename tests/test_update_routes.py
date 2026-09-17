import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app as api
from model import Base, Customer, CustomerGeneratorAsset, HydrogenGenerator
from schemas.customer import CustomerSchema, CustomerSearchSchema
from schemas.customer_generator_asset import (
    CustomerGeneratorAssetSchema,
    CustomerGeneratorAssetSearchSchema,
)
from schemas.hydrogen_generator import (
    HydrogenGeneratorCreateSchema,
    HydrogenGeneratorSearchSchema,
)


class UpdateRouteTests(unittest.TestCase):
    def setUp(self):
        self.original_session_factory = api.Session
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        api.Session = self.session_factory

        session = self.session_factory()
        first_customer = Customer(
            "First Customer", "first@example.com", "111-22-3333"
        )
        second_customer = Customer(
            "Second Customer", "second@example.com", "444-55-6666"
        )
        first_generator = self.make_generator("GEN-0001")
        second_generator = self.make_generator("GEN-0002")
        session.add_all(
            (first_customer, second_customer, first_generator, second_generator)
        )
        session.commit()

        self.first_customer_id = first_customer.customer_id
        self.second_customer_id = second_customer.customer_id
        self.first_generator_id = first_generator.generator_id
        self.second_generator_id = second_generator.generator_id
        asset = CustomerGeneratorAsset(
            self.first_customer_id,
            self.first_generator_id,
            1,
            datetime(2026, 1, 1),
        )
        session.add(asset)
        session.commit()
        self.asset_id = asset.asset_id
        session.close()

    def tearDown(self):
        api.Session = self.original_session_factory
        self.engine.dispose()

    @staticmethod
    def make_generator(serial_number: str) -> HydrogenGenerator:
        return HydrogenGenerator(
            serial_number,
            "Leasing",
            "PEMFC",
            10,
            100,
            1,
            24,
            16,
            12,
            20,
        )

    @staticmethod
    def generator_form(serial_number: str) -> HydrogenGeneratorCreateSchema:
        return HydrogenGeneratorCreateSchema(
            serial_number=serial_number,
            acquisition_type="Renting",
            stack_type="SOFC",
            number_of_cells=20,
            stack_voltage=200,
            current_density=2,
            length_in=24,
            width_in=16,
            height_in=12,
            weight_lb=25,
        )

    def test_put_routes_are_registered(self):
        put_routes = {
            rule.rule
            for rule in api.app.url_map.iter_rules()
            if "PUT" in rule.methods
        }

        self.assertTrue({"/customer", "/hydrogen-generator", "/asset"} <= put_routes)

    def test_updates_customer(self):
        body, status = api.update_customer(
            CustomerSearchSchema(customer_id=self.first_customer_id),
            CustomerSchema(
                name="Updated Customer",
                email="updated@example.com",
                tx_id="777-88-9999",
            ),
        )

        self.assertEqual(status, 200)
        self.assertEqual(body["name"], "Updated Customer")
        self.assertEqual(body["email"], "updated@example.com")

    def test_rejects_customer_uniqueness_conflict(self):
        body, status = api.update_customer(
            CustomerSearchSchema(customer_id=self.first_customer_id),
            CustomerSchema(
                name="Second Customer",
                email="unique@example.com",
                tx_id="777-88-9999",
            ),
        )

        self.assertEqual(status, 409)
        self.assertIn("same name", body["message"])

    def test_updates_generator_and_serial_number(self):
        body, status = api.update_hydrogen_generator(
            HydrogenGeneratorSearchSchema(serial_number="GEN-0001"),
            self.generator_form("GEN-0003"),
        )

        self.assertEqual(status, 200)
        self.assertEqual(body["serial_number"], "GEN-0003")
        self.assertEqual(body["acquisition_type"], "Renting")

    def test_updates_asset_and_preserves_omitted_installation_date(self):
        body, status = api.update_asset(
            CustomerGeneratorAssetSearchSchema(asset_id=self.asset_id),
            CustomerGeneratorAssetSchema(
                customer_id=self.second_customer_id,
                generator_id=self.second_generator_id,
                generator_qtd=3,
            ),
        )

        self.assertEqual(status, 200)
        self.assertEqual(body["customer_id"], self.second_customer_id)
        self.assertEqual(body["generator_id"], self.second_generator_id)
        self.assertEqual(body["generator_qtd"], 3)
        self.assertEqual(body["installation_date"], datetime(2026, 1, 1))

    def test_rejects_asset_with_missing_foreign_key(self):
        body, status = api.update_asset(
            CustomerGeneratorAssetSearchSchema(asset_id=self.asset_id),
            CustomerGeneratorAssetSchema(
                customer_id=999,
                generator_id=self.first_generator_id,
                generator_qtd=1,
            ),
        )

        self.assertEqual(status, 404)
        self.assertIn("Customer", body["message"])


if __name__ == "__main__":
    unittest.main()