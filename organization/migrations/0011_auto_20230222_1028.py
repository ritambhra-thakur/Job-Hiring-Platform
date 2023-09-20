# Generated by Django 3.2.16 on 2023-02-22 10:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0010_auto_20221110_1637'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='total_employee',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='organization',
            name='total_hired',
            field=models.IntegerField(default=0),
        ),
    ]
