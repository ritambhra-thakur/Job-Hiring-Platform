# Generated by Django 3.2.16 on 2023-03-01 11:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('primary_data', '0020_alter_industry_name'),
        ('form', '0098_auto_20230224_0739'),
    ]

    operations = [
        migrations.AddField(
            model_name='offerlettertemplate',
            name='city',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='offer_letter_ctiy', to='primary_data.city'),
        ),
        migrations.AddField(
            model_name='offerlettertemplate',
            name='employment_type',
            field=models.CharField(blank=True, default=None, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='offerlettertemplate',
            name='job_category',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='offer_letter_job_category', to='form.jobcategory'),
        ),
        migrations.AddField(
            model_name='offerlettertemplate',
            name='state',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='offer_letter_state', to='primary_data.state'),
        ),
        migrations.AlterField(
            model_name='offerlettertemplate',
            name='country',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='offer_letter_country', to='primary_data.country'),
        ),
    ]
