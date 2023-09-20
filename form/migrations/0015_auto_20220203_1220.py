# Generated by Django 3.2.9 on 2022-02-03 12:20

from django.db import migrations
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('form', '0014_auto_20220202_1025'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalpositionapproval',
            name='slug',
            field=django_extensions.db.fields.AutoSlugField(blank=True, editable=False, populate_from=['position', 'company', 'profile']),
        ),
        migrations.AlterField(
            model_name='positionapproval',
            name='slug',
            field=django_extensions.db.fields.AutoSlugField(blank=True, editable=False, populate_from=['position', 'company', 'profile']),
        ),
    ]
