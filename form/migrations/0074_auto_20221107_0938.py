# Generated by Django 3.2.13 on 2022-11-07 09:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('form', '0073_merge_20221107_0759'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='formdata',
            name='hiring_manager',
        ),
        migrations.RemoveField(
            model_name='formdata',
            name='recruiter',
        ),
    ]
