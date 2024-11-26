from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import CustomUser
from django.utils import timezone
from django.db import IntegrityError
from unittest import mock
from unittest.mock import patch

from .models import OCLDataImport, OCLPrice
from .forms import OCLDownloadForm
from .utils import get_historical_data, parse_row
from .views import fetch_and_save_ocl_data

import pandas as pd

class ViewsTestCase(TestCase):
    def setUp(self):
        # Create a user
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
        self.assertRedirects(response, '/accounts/login/?next=/data/')  # Adjust URL as needed

    def test_data_view_logged_in(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('data_view'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'data/data.html')
        self.assertIn('ocl_data_imports', response.context)
        self.assertIn('page_obj', response.context)

    @mock.patch('data.views.Paginator')
    def test_data_view_pagination(self, mock_paginator):
        self.client.login(username='testuser', password='testpassword')
        # Mock the paginator to return a specific page
        mock_page = mock.Mock()
        mock_paginator.return_value.get_page.return_value = mock_page
        response = self.client.get(reverse('data_view') + '?page=2')
        self.assertEqual(response.status_code, 200)
        mock_paginator.assert_called_once()
        self.assertIn('page_obj', response.context)

    def test_data_import_view_get_requires_login(self):
        response = self.client.get(reverse('data_import_view'))
        self.assertRedirects(response, '/accounts/login/?next=/data_import_view/')  # Adjust URL as needed

    def test_data_import_view_get_logged_in(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('data_import_view'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'data/data_import.html')
        self.assertIsInstance(response.context['form'], OCLDownloadForm)

    @patch('data.views.fetch_and_save_ocl_data.delay')
    def test_data_import_view_post_valid_form(self, mock_fetch_task):
        self.client.login(username='testuser', password='testpassword')
        form_data = {
            'asset': 'ETH',
            'interval': '15m',
            'start_date': (timezone.now().date() - timezone.timedelta(days=5)).isoformat(),
            'end_date': timezone.now().date().isoformat(),
        }
        response = self.client.post(reverse('data_import_view'), data=form_data)
        self.assertRedirects(response, reverse('data_view'))
        # Check that the data_import was created
        self.assertTrue(OCLDataImport.objects.filter(asset='ETH').exists())
        data_import = OCLDataImport.objects.get(asset='ETH')
        # Check that the Celery task was called
        mock_fetch_task.assert_called_once_with(data_import.id)

    def test_data_import_view_post_invalid_form(self):
        self.client.login(username='testuser', password='testpassword')
        form_data = {
            'asset': 'INVALID_ASSET',  # Assuming 'INVALID_ASSET' is not a valid choice
            'interval': '15m',
            'start_date': 'invalid-date',
            'end_date': 'invalid-date',
        }
        response = self.client.post(reverse('data_import_view'), data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'data/data_import.html')
        self.assertFormError(response, 'form', 'asset', 'Select a valid choice. INVALID_ASSET is not one of the available choices.')
        self.assertFormError(response, 'form', 'start_date', 'Enter a valid date.')
        self.assertFormError(response, 'form', 'end_date', 'Enter a valid date.')

    @patch('data.views.get_historical_data')
    @patch('data.views.parse_row')
    def test_fetch_and_save_ocl_data_success(self, mock_parse_row, mock_get_historical_data):
        # Mock get_historical_data to return a DataFrame
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

        # Mock parse_row to return dictionary
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

        # Call the task
        fetch_and_save_ocl_data(self.data_import.id)

        # Refresh from DB
        self.data_import.refresh_from_db()

        # Assertions
        self.assertEqual(self.data_import.status, 'completed')
        self.assertEqual(self.data_import.start_date, mock_df.iloc[0]['Date'].date())
        self.assertEqual(self.data_import.end_date, mock_df.iloc[-1]['Date'].date())
        # Check that OCLPrice objects were created
        self.assertEqual(OCLPrice.objects.filter(data_import=self.data_import).count(), 2)

    @patch('data.views.get_historical_data')
    @patch('data.views.parse_row')
    def test_fetch_and_save_ocl_data_integrity_error(self, mock_parse_row, mock_get_historical_data):
        # Mock get_historical_data to return a DataFrame
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

        # Mock parse_row to return dictionary
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

        # Create an IntegrityError when creating the second OCLPrice
        with patch('data.models.OCLPrice.objects.create', side_effect=[None, IntegrityError()]):
            fetch_and_save_ocl_data(self.data_import.id)

            # Refresh from DB
            self.data_import.refresh_from_db()

            # Assertions
            self.assertEqual(self.data_import.status, 'failed')
            # Only one OCLPrice should have been created before the error
            self.assertEqual(OCLPrice.objects.filter(data_import=self.data_import).count(), 1)

    def test_parse_row_called_correctly_in_task(self):
        with patch('data.views.parse_row') as mock_parse_row, \
             patch('data.views.get_historical_data') as mock_get_historical_data:
            # Setup mock
            mock_df = pd.DataFrame({
                'Date': [timezone.now()],
                'Open': [50000.0],
                'High': [50500.0],
                'Low': [49500.0],
                'Close': [50200.0],
                'Volume': [1500.5]
            })
            mock_get_historical_data.return_value = mock_df
            mock_parse_row.return_value = {
                'date': mock_df.iloc[0]['Date'],
                'open': mock_df.iloc[0]['Open'],
                'high': mock_df.iloc[0]['High'],
                'low': mock_df.iloc[0]['Low'],
                'close': mock_df.iloc[0]['Close'],
                'volume': mock_df.iloc[0]['Volume']
            }

            # Call the task
            fetch_and_save_ocl_data(self.data_import.id)

            # Check that parse_row was called with the correct row
            mock_parse_row.assert_called_once_with(mock_df.iloc[0])

    def test_fetch_and_save_ocl_data_invalid_data_import(self):
        # Call the task with non-existing id
        with self.assertRaises(OCLDataImport.DoesNotExist):
            fetch_and_save_ocl_data(9999)  # Assuming this ID does not exist


class CeleryTaskTestCase(TestCase):
    @patch('data.views.get_historical_data')
    @patch('data.views.parse_row')
    def test_celery_task_fetch_and_save(self, mock_parse_row, mock_get_historical_data):
        """
        Test the Celery task fetch_and_save_ocl_data.
        """
        # Mock get_historical_data to return a DataFrame
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

        # Mock parse_row to return dictionaries
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

        # Call the task
        with mock.patch('data.models.OCLPrice.objects.create') as mock_create:
            fetch_and_save_ocl_data(self.data_import.id)
            # Assert that create was called twice
            self.assertEqual(mock_create.call_count, 2)
            # Check that status was updated to 'completed'
            self.data_import.refresh_from_db()
            self.assertEqual(self.data_import.status, 'completed')