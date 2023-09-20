# Generated by Django 3.2.13 on 2022-05-09 03:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('form', '0037_alter_reason_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reason',
            name='type',
            field=models.CharField(choices=[('Position Rejection', 'position_r'), ('Offer Rejection', 'offer_r'), ('Candidate Rejection', 'candidate_r'), ('Position Hold', 'position_h'), ('Offer Hold', 'offer_h'), ('Candidate Hold', 'candidate_h')], default='Onhold', max_length=50),
        ),
    ]
