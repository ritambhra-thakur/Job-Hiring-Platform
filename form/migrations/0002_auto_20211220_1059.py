# Generated by Django 3.2.9 on 2021-12-20 10:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('form', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='field',
            name='field_type',
            field=models.CharField(blank=True, choices=[('string', 'string'), ('intiger', 'intiger'), ('boolean', 'boolean')], max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='historicalfield',
            name='field_type',
            field=models.CharField(blank=True, choices=[('string', 'string'), ('intiger', 'intiger'), ('boolean', 'boolean')], max_length=50, null=True),
        ),
    ]
