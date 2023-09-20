from django.db import migrations, models
import user.models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0030_team"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="user_refereed_by",
            field=models.JSONField(default=user.models.default_json),
        ),
    ]
