from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("health", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="medicalreport",
            name="report_file",
            field=models.FileField(blank=True, null=True, upload_to="reports/"),
        ),
    ]
