# Generated by Django 3.2.9 on 2022-03-24 07:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0019_auto_20220315_0606'),
        ('form', '0033_auto_20220323_1156'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appliedposition',
            name='refereed_by_profile',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='refereed_by_profile', to='user.profile'),
        ),
    ]
