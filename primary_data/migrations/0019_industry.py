# Generated by Django 3.2.16 on 2023-01-31 10:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('primary_data', '0018_alter_education_passing_out_year'),
    ]

    operations = [
        migrations.CreateModel(
            name='Industry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Enter industry name', max_length=150)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='created date and time', null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='updated date and time', null=True)),
            ],
            options={
                'verbose_name_plural': 'industries',
            },
        ),
    ]
