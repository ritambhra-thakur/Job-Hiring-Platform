# Generated by Django 3.2.16 on 2023-01-27 10:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0046_auto_20230117_1124'),
    ]

    operations = [
        migrations.CreateModel(
            name='OktaState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('state', models.CharField(max_length=255)),
                ('code_challenge', models.CharField(max_length=255)),
            ],
        ),
    ]
