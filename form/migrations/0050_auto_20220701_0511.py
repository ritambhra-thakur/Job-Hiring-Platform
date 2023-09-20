# Generated by Django 3.2.13 on 2022-07-01 05:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('form', '0049_alter_appliedposition_application_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReasonType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason_name', models.CharField(blank=True, help_text='Enter Reason Name', max_length=50, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='created date and time', null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='updated date and time', null=True)),
            ],
        ),
        migrations.AlterField(
            model_name='reason',
            name='type',
            field=models.CharField(choices=[('Position Rejection', 'position_r'), ('Offer Rejection', 'offer_r'), ('Candidate Rejection', 'candidate_r'), ('Position Hold', 'position_h'), ('Offer Hold', 'offer_h'), ('Candidate Hold', 'candidate_h'), ('Reject', 'reject')], default='Onhold', max_length=50),
        ),
    ]
