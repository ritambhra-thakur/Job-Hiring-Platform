# Generated by Django 3.2.13 on 2022-05-24 04:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stage', '0011_alter_positionstage_competency'),
        ('scorecard', '0013_positionscorecard_position_stage'),
    ]

    operations = [
        migrations.AlterField(
            model_name='positionscorecard',
            name='position_stage',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='stage.stage'),
        ),
    ]
