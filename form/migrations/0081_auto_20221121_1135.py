# Generated by Django 3.2.16 on 2022-11-21 11:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('form', '0080_offerletter_reporting_manager'),
    ]

    operations = [
        migrations.AddField(
            model_name='offerletter',
            name='created_at',
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name='offerletter',
            name='response_date',
            field=models.DateField(blank=True, default=None, null=True),
        ),
    ]
