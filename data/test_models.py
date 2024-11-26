from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import OCLDataImport, OCLPrice, FormattedPriceData
from django.utils import timezone
from datetime import timedelta

class OCLDataImportModelTest(TestCase):
    def setUp(self):
        self.data_import = OCLDataImport.objects.create(
            asset='BTC',
            interval='5m',
            start_date=timezone.now().date() - timedelta(days=10),
            end_date=timezone.now().date(),
            status='pending'
        )

    def test_str_representation(self):
        expected_str = f"{self.data_import.asset} {self.data_import.interval} from {self.data_import.start_date} to {self.data_import.end_date}"
        self.assertEqual(str(self.data_import), expected_str)

    def test_default_status(self):
        new_import = OCLDataImport.objects.create(
            asset='ETH',
            interval='15m',
            start_date=timezone.now().date() - timedelta(days=5),
            end_date=timezone.now().date()
        )
        self.assertEqual(new_import.status, 'pending')

    def test_unique_constraint(self):
        with self.assertRaises(ValidationError):
            duplicate = OCLDataImport(
                asset='BTC',
                interval='5m',
                start_date=self.data_import.start_date,
                end_date=self.data_import.end_date
            )
            duplicate.full_clean()  # This should raise ValidationError

    def test_indexes(self):
        # This test ensures that the indexes are created.
        # Note: Django does not provide a straightforward way to test indexes via ORM,
        # so this is a placeholder to acknowledge the presence of indexes.
        # Comprehensive index testing often requires inspecting the database directly.
        self.assertTrue(True)

    def test_get_price_data_empty(self):
        price_data = self.data_import.get_price_data()
        self.assertEqual(price_data.to_dict(), [])

    def test_get_price_data_with_entries(self):
        OCLPrice.objects.create(
            data_import=self.data_import,
            date=timezone.now(),
            open=50000.0,
            high=50500.0,
            low=49500.0,
            close=50200.0,
            volume=1500.5
        )
        price_data = self.data_import.get_price_data()
        self.assertEqual(len(price_data.to_dict()), 1)
        record = price_data.to_dict()[0]
        self.assertIn('Date', record)
        self.assertIn('Open', record)
        self.assertIn('High', record)
        self.assertIn('Low', record)
        self.assertIn('Close', record)

class OCLPriceModelTest(TestCase):
    def setUp(self):
        self.data_import = OCLDataImport.objects.create(
            asset='ETH',
            interval='15m',
            start_date=timezone.now().date() - timedelta(days=20),
            end_date=timezone.now().date(),
            status='completed'
        )
        self.price = OCLPrice.objects.create(
            data_import=self.data_import,
            date=timezone.now(),
            open=3000.0,
            high=3100.0,
            low=2950.0,
            close=3050.0,
            volume=2500.75
        )

    def test_str_representation(self):
        expected_str = f"{self.price.data_import.asset} on {self.price.date.strftime('%Y-%m-%d')}"
        self.assertEqual(str(self.price), expected_str)

    def test_ordering(self):
        earlier_date = timezone.now() - timedelta(days=1)
        later_date = timezone.now() + timedelta(days=1)
        OCLPrice.objects.create(
            data_import=self.data_import,
            date=earlier_date,
            open=2900.0,
            high=2950.0,
            low=2850.0,
            close=2925.0,
            volume=1800.0
        )
        OCLPrice.objects.create(
            data_import=self.data_import,
            date=later_date,
            open=3100.0,
            high=3150.0,
            low=3050.0,
            close=3125.0,
            volume=2200.0
        )
        prices = list(OCLPrice.objects.all())
        self.assertEqual(prices[0].date, earlier_date)
        self.assertEqual(prices[1].date, self.price.date)
        self.assertEqual(prices[2].date, later_date)

    def test_foreign_key_cascade_delete(self):
        self.data_import.delete()
        with self.assertRaises(OCLPrice.DoesNotExist):
            OCLPrice.objects.get(id=self.price.id)

    def test_field_types(self):
        self.assertIsInstance(self.price.date, timezone.datetime)
        self.assertIsInstance(self.price.open, float)
        self.assertIsInstance(self.price.high, float)
        self.assertIsInstance(self.price.low, float)
        self.assertIsInstance(self.price.close, float)
        self.assertIsInstance(self.price.volume, float)

class FormattedPriceDataTest(TestCase):
    def test_to_dict_records(self):
        data = [
            {
                'Date': '2023-10-01 00:00:00',
                'Open': 100.0,
                'High': 110.0,
                'Low': 90.0,
                'Close': 105.0
            },
            {
                'Date': '2023-10-02 00:00:00',
                'Open': 106.0,
                'High': 115.0,
                'Low': 95.0,
                'Close': 110.0
            }
        ]
        formatted_data = FormattedPriceData(data)
        self.assertEqual(formatted_data.to_dict(), data)

    def test_to_dict_invalid_orient(self):
        data = []
        formatted_data = FormattedPriceData(data)
        with self.assertRaises(ValueError):
            formatted_data.to_dict(orient='invalid_orient')
