# Generated by Django 3.2.9 on 2022-03-15 06:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('role', '0016_auto_20220225_0952'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='historicalrole',
            name='company',
        ),
        migrations.RemoveField(
            model_name='historicalrole',
            name='history_user',
        ),
        migrations.RemoveField(
            model_name='historicalrolelist',
            name='history_user',
        ),
        migrations.RemoveField(
            model_name='historicalrolepermission',
            name='access',
        ),
        migrations.RemoveField(
            model_name='historicalrolepermission',
            name='history_user',
        ),
        migrations.RemoveField(
            model_name='historicalrolepermission',
            name='role',
        ),
        migrations.DeleteModel(
            name='HistoricalAccess',
        ),
        migrations.DeleteModel(
            name='HistoricalRole',
        ),
        migrations.DeleteModel(
            name='HistoricalRoleList',
        ),
        migrations.DeleteModel(
            name='HistoricalRolePermission',
        ),
    ]
