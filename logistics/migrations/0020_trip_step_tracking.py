# Generated manually for driver trip step tracking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('logistics', '0019_dbsdecanting_post_decant_photo_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='trip',
            name='current_step',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='trip',
            name='step_data',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='trip',
            name='last_activity_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
