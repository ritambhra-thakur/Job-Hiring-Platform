# Generated by Django 3.2.16 on 2023-05-09 12:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0050_auto_20230321_0456'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='was_candidate',
            field=models.BooleanField(blank=True, default=None, null=True),
        ),
    ]
