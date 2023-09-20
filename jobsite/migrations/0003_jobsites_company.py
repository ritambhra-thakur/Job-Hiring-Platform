# Generated by Django 3.2.9 on 2022-04-25 10:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0005_department'),
        ('jobsite', '0002_auto_20220425_1013'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobsites',
            name='company',
            field=models.ForeignKey(blank=True, help_text='Choose your company name', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='job_site_company', to='company.company'),
        ),
    ]
