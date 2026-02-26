from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MedicalReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('report_file', models.FileField(upload_to='reports/')),
                ('report_date', models.DateField()),
                ('analysis_completed', models.BooleanField(default=False)),
                ('ocr_text', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='medical_reports', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-report_date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='LabParameter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('value', models.FloatField()),
                ('unit', models.CharField(blank=True, max_length=30)),
                ('ref_min', models.FloatField(blank=True, null=True)),
                ('ref_max', models.FloatField(blank=True, null=True)),
                ('risk_flag', models.CharField(choices=[('normal', 'Normal'), ('low', 'Low'), ('high', 'High'), ('unknown', 'Unknown')], default='unknown', max_length=20)),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parameters', to='health.medicalreport')),
            ],
        ),
        migrations.CreateModel(
            name='AnalysisResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mentor_summary', models.TextField(blank=True)),
                ('trend_analysis', models.TextField(blank=True)),
                ('doctor_summary', models.TextField(blank=True)),
                ('raw_response', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('report', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='analysis', to='health.medicalreport')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='analysis_results', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
