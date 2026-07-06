from types import SimpleNamespace
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.routes.transactions import request_deposit
from app.core.database import Base
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate


class DepositScreenshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.session = Session(bind=self.engine)

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_deposit_requires_screenshot(self) -> None:
        user = SimpleNamespace(id=1)
        with self.assertRaises(Exception) as ctx:
            request_deposit(
                payload=TransactionCreate(amount=100, note="demo"),
                user=user,
                db=self.session,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_deposit_requires_reference_note(self) -> None:
        user = SimpleNamespace(id=1)
        with self.assertRaises(Exception) as ctx:
            request_deposit(
                payload=TransactionCreate(amount=100, screenshot_data="data:image/png;base64,abc123"),
                user=user,
                db=self.session,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_deposit_saves_screenshot_per_transaction(self) -> None:
        user = SimpleNamespace(id=1)
        payload = TransactionCreate(
            amount=125,
            note="demo",
            screenshot_data="data:image/png;base64,abc123",
        )

        tx = request_deposit(payload=payload, user=user, db=self.session)

        stored = self.session.get(Transaction, tx.id)
        self.assertIsNotNone(stored)
        self.assertEqual(stored.screenshot_data, payload.screenshot_data)
        self.assertEqual(stored.user_id, user.id)


if __name__ == "__main__":
    unittest.main()
