# Generated by Django 3.2.9 on 2022-03-08 09:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('primary_data', '0014_auto_20220113_0515'),
        ('company', '0003_auto_20220113_0515'),
        ('referral', '0007_alter_referral_currency'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Referral',
            new_name='ReferralPolicy',
        ),
    ]
