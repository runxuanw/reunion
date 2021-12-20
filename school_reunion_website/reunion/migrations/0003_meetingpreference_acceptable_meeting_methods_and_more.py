# Generated by Django 4.0 on 2021-12-20 04:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reunion', '0002_meetingpreference'),
    ]

    operations = [
        migrations.AddField(
            model_name='meetingpreference',
            name='acceptable_meeting_methods',
            field=models.CharField(max_length=30, null=True),
        ),
        migrations.AddField(
            model_name='meetingpreference',
            name='acceptable_meeting_time_range_in_day',
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='meetingpreference',
            name='acceptable_offline_meeting_locations',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='meetingpreference',
            name='expected_attending_time_zones',
            field=models.CharField(max_length=300, null=True),
        ),
        migrations.AddField(
            model_name='meetingpreference',
            name='minimal_meeting_size',
            field=models.IntegerField(default=2),
        ),
        migrations.AddField(
            model_name='meetingpreference',
            name='minimal_meeting_value',
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name='meetingpreference',
            name='one_time_available_dates',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='meetingpreference',
            name='preferred_attending_frequency_in_months',
            field=models.IntegerField(default=12),
        ),
        migrations.AddField(
            model_name='meetingpreference',
            name='preferred_meeting_activities',
            field=models.CharField(max_length=300, null=True),
        ),
        migrations.AddField(
            model_name='meetingpreference',
            name='preferred_meeting_duration_in_hour',
            field=models.DurationField(null=True),
        ),
        migrations.AddField(
            model_name='meetingpreference',
            name='repeated_available_dates_each_year',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='meetingpreference',
            name='repeated_available_holidays',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='meetingpreference',
            name='weighted_attendants',
            field=models.TextField(null=True),
        ),
    ]
