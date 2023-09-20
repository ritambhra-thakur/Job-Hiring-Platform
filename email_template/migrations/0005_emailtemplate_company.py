# Generated by Django 3.2.9 on 2022-04-28 07:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0005_department'),
        ('email_template', '0004_alter_emailtemplate_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailtemplate',
            name='company',
            field=models.ForeignKey(blank=True, help_text='Choose your company name', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='email_template_company', to='company.company'),
        ),
    ]
