# Generated by Django 3.2.13 on 2022-11-07 11:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('form', '0075_merge_20221107_1106'),
    ]

    operations = [
        migrations.AddField(
            model_name='formdata',
            name='hiring_manager',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='formdata',
            name='recruiter',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
