# Generated by Django 3.2.16 on 2023-01-13 09:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0043_auto_20230111_0415'),
    ]

    operations = [
        migrations.AddField(
            model_name='customquestion',
            name='is_mandatory',
            field=models.BooleanField(default=True),
        ),
    ]
