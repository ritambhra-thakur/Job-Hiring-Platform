# Generated by Django 3.2.9 on 2022-02-03 06:49

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('role', '0010_auto_20220202_1151'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='HistoricalPermission',
            new_name='HistoricalUserPermission',
        ),
        migrations.RenameModel(
            old_name='Permission',
            new_name='UserPermission',
        ),
        migrations.AlterModelOptions(
            name='historicaluserpermission',
            options={'get_latest_by': 'history_date', 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'historical user permission'},
        ),
        migrations.AlterModelTable(
            name='historicaluserpermission',
            table='user_permission_history',
        ),
    ]
