# Generated by Django 3.2.16 on 2023-01-17 09:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('form', '0091_offerlettertemplate_company'),
    ]

    operations = [
        migrations.AddField(
            model_name='offerletter',
            name='email_changed',
            field=models.BooleanField(default=False),
        ),
    ]
