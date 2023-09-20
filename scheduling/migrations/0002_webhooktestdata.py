# Generated by Django 3.2.16 on 2023-02-06 11:12

from django.db import migrations, models
import scheduling.models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='WebhookTestData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.JSONField(default=scheduling.models.get_json_default)),
            ],
        ),
    ]
