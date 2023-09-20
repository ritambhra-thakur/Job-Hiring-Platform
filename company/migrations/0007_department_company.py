# Generated by Django 3.2.16 on 2022-12-26 04:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0006_company_company_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='department',
            name='company',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='company.company'),
        ),
    ]
