# Generated by Django 3.2.13 on 2022-10-26 08:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('form', '0062_offerletter'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appliedposition',
            name='application_status',
            field=models.CharField(choices=[('reject', 'reject'), ('active', 'active'), ('hold', 'hold'), ('hired', 'hired'), ('kiv', 'kiv')], default='active', max_length=15),
        ),
    ]
