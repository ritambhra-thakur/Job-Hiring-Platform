# Generated by Django 3.2.9 on 2022-03-15 06:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0018_rename_profile_id_profile_employee_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='historicaluser',
            name='history_user',
        ),
        migrations.RemoveField(
            model_name='historicaluser',
            name='user_company',
        ),
        migrations.RemoveField(
            model_name='historicaluser',
            name='user_role',
        ),
        migrations.DeleteModel(
            name='HistoricalMedia',
        ),
        migrations.DeleteModel(
            name='HistoricalUser',
        ),
    ]
