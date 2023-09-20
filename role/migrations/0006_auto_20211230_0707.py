# Generated by Django 3.2.9 on 2021-12-30 07:07

from django.db import migrations
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('role', '0005_delete_rolepermissions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalrole',
            name='slug',
            field=django_extensions.db.fields.AutoSlugField(blank=True, editable=False, populate_from=['name', 'company']),
        ),
        migrations.AlterField(
            model_name='role',
            name='slug',
            field=django_extensions.db.fields.AutoSlugField(blank=True, editable=False, populate_from=['name', 'company']),
        ),
    ]
