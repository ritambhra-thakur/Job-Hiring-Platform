# Generated by Django 3.2.16 on 2023-04-19 06:29

from django.db import migrations, models
import form.models


class Migration(migrations.Migration):

    dependencies = [
        ('form', '0109_alter_offerapproval_approval_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='formdata',
            name='history',
            field=models.JSONField(default=form.models.get_json_default_list),
        ),
    ]
