# Generated by Django 3.2.16 on 2023-02-08 06:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0002_webhooktestdata'),
    ]

    operations = [
        migrations.AddField(
            model_name='webhooktestdata',
            name='msg',
            field=models.CharField(blank=True, default='No Message', max_length=255, null=True),
        ),
    ]
