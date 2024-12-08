from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import CustomUser
from django.utils import timezone
from django.db import IntegrityError
from unittest import mock
from unittest.mock import patch, MagicMock

from .models import OCLDataImport, OCLPrice
from .forms import OCLDownloadForm
from .views import fetch_and_save_ocl_data
import pandas as pd
from django.core.paginator import Page, Paginator

class ViewsTestCase(TestCase):
    def setUp(self):
        # Create a user with email (assuming CustomUser uses email as USERNAME_FIELD)
        self.user = CustomUser.objects.create_user(email='testuser@example.com', password='testpassword')
        self.client = Client()

        # Create a sample OCLDataImport
        self.data_import = OCLDataImport.objects.create(
            asset='BTC',
            interval='5m',
            start_date=timezone.now().date() - timezone.timedelta(days=10),
            end_date=timezone.now().date(),
            status='pending'
        )

    def test_data_view_requires_login(self):
        response = self.client.get(reverse('data_view'))
        login_url = reverse('login')
        expected_redirect = f'{login_url}?next={reverse("data_view")}'
        self.assertRedirects(response, expected_redirect)

    def test_data_view_logged_in(self):
        self.client.login(username='testuser@example.com', password='testpassword')
        response = self.client.get(reverse('data_view'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'data/data.html')
        self.assertIn('ocl_data_imports', response.context)
        self.assertIn('page_obj', response.context)

    @mock.patch('data.views.Paginator')
    def test_data_view_pagination(self, mock_paginator):
        # Simulate a real Page object
        self.client.login(username='testuser@example.com', password='testpassword')
        
        # Mock paginator instance
        paginator_instance = mock_paginator.return_value
        paginator_instance.num_pages = 2

        # Mock a Page-like object. A Page object usually can be iterated over.
        mock_page = MagicMock(spec=Page)
        mock_page.__iter__.return_value = []  # no items, just an empty page
        mock_page.number = 2
        mock_page.has_other_pages.return_value = True
        mock_page.paginator = paginator_instance

        paginator_instance.get_page.return_value = mock_page
        
        response = self.client.get(reverse('data_view') + '?page=2')
        self.assertEqual(response.status_code, 200)
        self.assertIn('page_obj', response.context)
        # Since template rendering requires iteration, no TypeError should occur now.

    def test_data_import_view_get_requires_login(self):
        response = self.client.get(reverse('data_import_view'))
        login_url = reverse('login')
        expected_redirect = f'{login_url}?next={reverse("data_import_view")}'
        self.assertRedirects(response, expected_redirect)

    def test_data_import_view_get_logged_in(self):
        self.client.login(username='testuser@example.com', password='testpassword')
        response = self.client.get(reverse('data_import_view'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'data/data_import.html')
        self.assertIsInstance(response.context['form'], OCLDownloadForm)

    @patch('data.views.fetch_and_save_ocl_data.delay')
    def test_data_import_view_post_valid_form(self, mock_fetch_task):
        self.client.login(username='testuser@example.com', password='testpassword')
        form_data = {
            'name': 'Test Import',  # Add a valid name here
            'asset': 'ETH',
            'interval': '15m',
            'start_date': (timezone.now().date() - timezone.timedelta(days=5)).isoformat(),
            'end_date': timezone.now().date().isoformat(),
        }
        response = self.client.post(reverse('data_import_view'), data=form_data)
        self.assertRedirects(response, reverse('data_view'))

        # Check that the data_import was created with 'ETH' (assuming ETH is valid)
        self.assertTrue(OCLDataImport.objects.filter(asset='ETH', name='Test Import').exists())
        data_import = OCLDataImport.objects.get(asset='ETH', name='Test Import')
        mock_fetch_task.assert_called_once_with(data_import.id)


    def test_data_import_view_post_invalid_form(self):
        self.client.login(username='testuser@example.com', password='testpassword')
        form_data = {
            'asset': '',  # Empty to force validation error if required
            'interval': '15m',
            'start_date': 'invalid-date',
            'end_date': 'invalid-date',
        }
        response = self.client.post(reverse('data_import_view'), data=form_data)
        # Ensure we got the form back with errors
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'data/data_import.html')
        form = response.context.get('form')
        self.assertIsNotNone(form)
        self.assertTrue(form.errors)
        # Adjust error messages as per the form validation (these may differ):
        self.assertIn('Enter a valid date.', form.errors.get('start_date', []))
        self.assertIn('Enter a valid date.', form.errors.get('end_date', []))

    @patch('data.views.get_historical_data')
    @patch('data.views.parse_row')
    def test_fetch_and_save_ocl_data_success(self, mock_parse_row, mock_get_historical_data):
        mock_df = pd.DataFrame({
            'Date': [
                timezone.now() - timezone.timedelta(minutes=5),
                timezone.now()
            ],
            'Open': [50000.0, 50200.0],
            'High': [50500.0, 50700.0],
            'Low': [49500.0, 49700.0],
            'Close': [50200.0, 50400.0],
            'Volume': [1500.5, 1600.5]
        })
        mock_get_historical_data.return_value = mock_df

        mock_parse_row.side_effect = [
            {
                'date': mock_df.iloc[0]['Date'],
                'open': mock_df.iloc[0]['Open'],
                'high': mock_df.iloc[0]['High'],
                'low': mock_df.iloc[0]['Low'],
                'close': mock_df.iloc[0]['Close'],
                'volume': mock_df.iloc[0]['Volume']
            },
            {
                'date': mock_df.iloc[1]['Date'],
                'open': mock_df.iloc[1]['Open'],
                'high': mock_df.iloc[1]['High'],
                'low': mock_df.iloc[1]['Low'],
                'close': mock_df.iloc[1]['Close'],
                'volume': mock_df.iloc[1]['Volume']
            }
        ]

        fetch_and_save_ocl_data(self.data_import.id)
        self.data_import.refresh_from_db()
        self.assertEqual(self.data_import.status, 'completed')
        self.assertEqual(self.data_import.start_date, mock_df.iloc[0]['Date'].date())
        self.assertEqual(self.data_import.end_date, mock_df.iloc[-1]['Date'].date())
        self.assertEqual(OCLPrice.objects.filter(data_import=self.data_import).count(), 2)

    @patch('data.views.get_historical_data')
    @patch('data.views.parse_row')
    def test_fetch_and_save_ocl_data_integrity_error(self, mock_parse_row, mock_get_historical_data):
        mock_df = pd.DataFrame({
            'Date': [
                timezone.now() - timezone.timedelta(minutes=5),
                timezone.now()
            ],
            'Open': [50000.0, 50200.0],
            'High': [50500.0, 50700.0],
            'Low': [49500.0, 49700.0],
            'Close': [50200.0, 50400.0],
            'Volume': [1500.5, 1600.5]
        })
        mock_get_historical_data.return_value = mock_df

        # Return valid rows for parse_row
        first_row_data = {
            'date': mock_df.iloc[0]['Date'],
            'open': mock_df.iloc[0]['Open'],
            'high': mock_df.iloc[0]['High'],
            'low': mock_df.iloc[0]['Low'],
            'close': mock_df.iloc[0]['Close'],
            'volume': mock_df.iloc[0]['Volume']
        }
        second_row_data = {
            'date': mock_df.iloc[1]['Date'],
            'open': mock_df.iloc[1]['Open'],
            'high': mock_df.iloc[1]['High'],
            'low': mock_df.iloc[1]['Low'],
            'close': mock_df.iloc[1]['Close'],
            'volume': mock_df.iloc[1]['Volume']
        }

        mock_parse_row.side_effect = [first_row_data, second_row_data]

        # On the first create, return a valid OCLPrice instance; on the second, raise IntegrityError
        first_price = OCLPrice(
            date=first_row_data['date'],
            open=first_row_data['open'],
            high=first_row_data['high'],
            low=first_row_data['low'],
            close=first_row_data['close'],
            volume=first_row_data['volume'],
            data_import=self.data_import
        )
        first_price.save() 

        with patch('data.models.OCLPrice.objects.create', side_effect=[IntegrityError()]):
            fetch_and_save_ocl_data(self.data_import.id)
            self.data_import.refresh_from_db()
            self.assertEqual(self.data_import.status, 'failed')
            self.assertEqual(OCLPrice.objects.filter(data_import=self.data_import).count(), 1)

    def test_parse_row_called_correctly_in_task(self):
        with patch('data.views.parse_row') as mock_parse_row, \
             patch('data.views.get_historical_data') as mock_get_historical_data:
            mock_df = pd.DataFrame({
                'Date': [timezone.now()],
                'Open': [50000.0],
                'High': [50500.0],
                'Low': [49500.0],
                'Close': [50200.0],
                'Volume': [1500.5]
            })
            mock_get_historical_data.return_value = mock_df

            # Provide a valid parse_row return value
            mock_parse_row.return_value = {
                'date': mock_df.iloc[0]['Date'],
                'open': mock_df.iloc[0]['Open'],
                'high': mock_df.iloc[0]['High'],
                'low': mock_df.iloc[0]['Low'],
                'close': mock_df.iloc[0]['Close'],
                'volume': mock_df.iloc[0]['Volume']
            }

            fetch_and_save_ocl_data(self.data_import.id)

            # Check that parse_row was called once
            mock_parse_row.assert_called_once()
            called_arg = mock_parse_row.call_args[0][0]
            pd.testing.assert_series_equal(called_arg, mock_df.iloc[0])

    def test_fetch_and_save_ocl_data_invalid_data_import(self):
        with self.assertRaises(OCLDataImport.DoesNotExist):
            fetch_and_save_ocl_data(9999)


class CeleryTaskTestCase(TestCase):
    @patch('data.views.get_historical_data')
    @patch('data.views.parse_row')
    def test_celery_task_fetch_and_save(self, mock_parse_row, mock_get_historical_data):
        mock_df = pd.DataFrame({
            'Date': [
                timezone.now() - timezone.timedelta(minutes=5),
                timezone.now()
            ],
            'Open': [50000.0, 50200.0],
            'High': [50500.0, 50700.0],
            'Low': [49500.0, 49700.0],
            'Close': [50200.0, 50400.0],
            'Volume': [1500.5, 1600.5]
        })
        mock_get_historical_data.return_value = mock_df
        mock_parse_row.side_effect = [
            {
                'date': mock_df.iloc[0]['Date'],
                'open': mock_df.iloc[0]['Open'],
                'high': mock_df.iloc[0]['High'],
                'low': mock_df.iloc[0]['Low'],
                'close': mock_df.iloc[0]['Close'],
                'volume': mock_df.iloc[0]['Volume']
            },
            {
                'date': mock_df.iloc[1]['Date'],
                'open': mock_df.iloc[1]['Open'],
                'high': mock_df.iloc[1]['High'],
                'low': mock_df.iloc[1]['Low'],
                'close': mock_df.iloc[1]['Close'],
                'volume': mock_df.iloc[1]['Volume']
            }
        ]

        # Create a DataImport to test the celery task
        data_import = OCLDataImport.objects.create(
            asset='BTC',
            interval='5m',
            start_date=timezone.now().date() - timezone.timedelta(days=10),
            end_date=timezone.now().date(),
            status='pending'
        )

        with patch('data.models.OCLPrice.objects.create') as mock_create:
            # Return valid OCLPrice objects
            first_price = OCLPrice(
                date=mock_df.iloc[0]['Date'],
                open=50000.0, high=50500.0, low=49500.0, close=50200.0, volume=1500.5,
                data_import=data_import
            )
            second_price = OCLPrice(
                date=mock_df.iloc[1]['Date'],
                open=50200.0, high=50700.0, low=49700.0, close=50400.0, volume=1600.5,
                data_import=data_import
            )
            mock_create.side_effect = [first_price, second_price]

            fetch_and_save_ocl_data(data_import.id)
            self.assertEqual(mock_create.call_count, 2)
            data_import.refresh_from_db()
            self.assertEqual(data_import.status, 'completed')
