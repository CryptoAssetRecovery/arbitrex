# Generated by Django 5.1.3 on 2024-11-23 20:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backtesting', '0004_alter_backtestresult_parameters'),
    ]

    operations = [
        migrations.AddField(
            model_name='backtestresult',
            name='strategy_code',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='backtestresult',
            name='strategy_description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='backtestresult',
            name='strategy_name',
            field=models.CharField(default='Default Name', max_length=100),
            preserve_default=False,
        ),
    ]
