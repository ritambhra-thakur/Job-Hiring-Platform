# Generated by Django 3.2.9 on 2022-02-15 08:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('form', '0017_auto_20220204_0624'),
    ]

    operations = [
        migrations.AddField(
            model_name='formdata',
            name='candidate_visibility',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='formdata',
            name='employee_visibility',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='historicalformdata',
            name='candidate_visibility',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='historicalformdata',
            name='employee_visibility',
            field=models.BooleanField(default=False),
        ),
    ]
