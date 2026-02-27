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
            name='LLMContextSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('context_json', models.JSONField()),
                ('source', models.CharField(blank=True, max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('age', models.IntegerField(blank=True, null=True)),
                ('gender', models.CharField(blank=True, max_length=20)),
                ('city', models.CharField(blank=True, max_length=100)),
                ('location_type', models.CharField(blank=True, choices=[('rural', 'Rural'), ('urban', 'Urban'), ('semi-urban', 'Semi Urban')], max_length=20)),
                ('sleep_hours', models.FloatField(blank=True, null=True)),
                ('activity_level', models.CharField(blank=True, max_length=50)),
                ('diet_type', models.CharField(blank=True, max_length=100)),
                ('occupation', models.CharField(blank=True, max_length=150)),
                ('past_medical_conditions', models.TextField(blank=True)),
                ('current_symptoms', models.TextField(blank=True)),
                ('medications', models.TextField(blank=True)),
                ('health_goal', models.CharField(blank=True, max_length=255)),
                ('language_preference', models.CharField(blank=True, max_length=50)),
                ('smoking_status', models.CharField(blank=True, max_length=50)),
                ('alcohol_consumption', models.CharField(blank=True, max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
