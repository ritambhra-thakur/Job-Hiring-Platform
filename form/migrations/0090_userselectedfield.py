# Generated by Django 3.2.16 on 2022-12-20 08:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0035_auto_20221219_1016'),
        ('form', '0089_auto_20221216_1142'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserSelectedField',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('selected_fields', models.JSONField()),
                ('select_type', models.CharField(max_length=255)),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user.profile')),
            ],
        ),
    ]
