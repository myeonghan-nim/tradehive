# Generated by Django 5.1.4 on 2025-02-05 08:30

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CryptoCurrency",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=50)),
                ("symbol", models.CharField(max_length=10)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "cryptocurrencies",
            },
        ),
        migrations.CreateModel(
            name="TradingPair",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("min_price", models.DecimalField(decimal_places=8, max_digits=20)),
                ("max_price", models.DecimalField(decimal_places=8, max_digits=20)),
                ("tick_size", models.DecimalField(decimal_places=8, max_digits=20)),
                ("min_quantity", models.DecimalField(decimal_places=8, max_digits=20)),
                ("max_quantity", models.DecimalField(decimal_places=8, max_digits=20)),
                ("step_size", models.DecimalField(decimal_places=8, max_digits=20)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("base_asset", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="base_asset", to="markets.cryptocurrency")),
                ("quote_asset", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="quote_asset", to="markets.cryptocurrency")),
            ],
            options={
                "db_table": "trading_pairs",
                "unique_together": {("base_asset", "quote_asset")},
            },
        ),
    ]
