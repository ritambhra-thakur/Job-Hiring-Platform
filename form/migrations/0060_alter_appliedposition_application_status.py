# Generated by Django 3.2.13 on 2022-10-13 10:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('form', '0059_field_can_delete'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appliedposition',
            name='application_status',
            field=models.CharField(choices=[('reject', 'reject'), ('active', 'active'), ('hold', 'hold'), ('hired', 'hired')], default='active', max_length=10),
        ),
    ]
