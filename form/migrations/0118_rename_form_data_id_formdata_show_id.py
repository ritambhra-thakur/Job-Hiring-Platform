# Generated by Django 3.2.16 on 2023-06-21 09:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('form', '0117_auto_20230621_0437'),
    ]

    operations = [
        migrations.RenameField(
            model_name='formdata',
            old_name='form_data_id',
            new_name='show_id',
        ),
    ]
