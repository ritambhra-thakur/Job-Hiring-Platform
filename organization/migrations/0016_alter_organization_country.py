# Generated by Django 3.2.16 on 2023-03-03 06:50

from django.db import migrations, models
import organization.models


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0015_organization_country'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organization',
            name='country',
            field=models.JSONField(default=organization.models.default_listed_dict),
        ),
    ]
