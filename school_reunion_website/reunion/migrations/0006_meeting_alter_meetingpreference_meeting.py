# Generated by Django 4.0 on 2021-12-20 08:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reunion', '0005_delete_choice_delete_question'),
    ]

    operations = [
        migrations.CreateModel(
            name='Meeting',
            fields=[
                ('meeting_code', models.UUIDField(primary_key=True, serialize=False)),
                ('display_name', models.CharField(max_length=100)),
                ('code_max_usage', models.IntegerField()),
                ('contact_email', models.EmailField(max_length=254)),
            ],
        ),
        migrations.AlterField(
            model_name='meetingpreference',
            name='meeting',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='reunion.meeting'),
        ),
    ]
