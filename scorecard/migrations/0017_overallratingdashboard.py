# Generated by Django 3.2.13 on 2022-10-14 11:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0029_user_encoded_id'),
        ('form', '0060_alter_appliedposition_application_status'),
        ('scorecard', '0016_alter_positionscorecard_competency'),
    ]

    operations = [
        migrations.CreateModel(
            name='OverAllRatingDashboard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.JSONField()),
                ('is_active', models.BooleanField(default=True, help_text='   ')),
                ('is_deleted', models.BooleanField(default=False, help_text='Check this box to delete the CandidatePositionDashboard')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='created date and time')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='updated date and time')),
                ('applied_position', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='form.appliedposition')),
                ('candidate_id', models.ForeignKey(blank=True, help_text='Enter Candidate ID', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='candidate_id', to='user.profile')),
                ('interviewer_id', models.ForeignKey(blank=True, help_text='Enter applied position', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='Candidate_position', to='user.profile')),
            ],
        ),
    ]
