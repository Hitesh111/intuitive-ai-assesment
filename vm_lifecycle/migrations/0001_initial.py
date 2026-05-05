from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='VMInstance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128, unique=True)),
                ('image_id', models.CharField(max_length=128)),
                ('flavor_id', models.CharField(max_length=128)),
                ('network_id', models.CharField(max_length=128)),
                ('key_name', models.CharField(blank=True, max_length=128)),
                ('provider_instance_id', models.CharField(max_length=128, unique=True)),
                ('status', models.CharField(choices=[('BUILDING', 'Building'), ('ACTIVE', 'Active'), ('STOPPED', 'Stopped'), ('ERROR', 'Error'), ('DELETED', 'Deleted')], default='BUILDING', max_length=16)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='VMActionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=32)),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('success', models.BooleanField(default=True)),
                ('details', models.JSONField(blank=True, default=dict)),
                ('vm', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='actions', to='vm_lifecycle.vminstance')),
            ],
            options={'ordering': ['-requested_at']},
        ),
    ]
