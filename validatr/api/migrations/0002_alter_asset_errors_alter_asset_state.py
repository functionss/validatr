# Generated by Django 4.1.1 on 2022-09-24 15:19

from django.db import migrations, models
import validatr.api.models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="asset",
            name="errors",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="asset",
            name="state",
            field=models.CharField(
                choices=[
                    (
                        validatr.api.models.QUEUED,
                        validatr.api.models.QUEUED,
                    ),
                    (
                        validatr.api.models.IN_PROGRESS,
                        validatr.api.models.IN_PROGRESS,
                    ),
                    (
                        validatr.api.models.COMPLETE,
                        validatr.api.models.COMPLETE,
                    ),
                    (
                        validatr.api.models.FAILED,
                        validatr.api.models.FAILED,
                    ),
                ],
                default="queued",
                max_length=16,
            ),
        ),
    ]
