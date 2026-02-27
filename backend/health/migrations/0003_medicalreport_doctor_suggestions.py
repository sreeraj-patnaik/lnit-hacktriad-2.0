from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("health", "0002_alter_medicalreport_report_file"),
    ]

    operations = [
        migrations.AddField(
            model_name="medicalreport",
            name="doctor_suggestions",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
