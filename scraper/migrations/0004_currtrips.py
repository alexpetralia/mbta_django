# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-01-17 19:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scraper', '0003_auto_20160110_2059'),
    ]

    operations = [
        migrations.CreateModel(
            name='CurrTrips',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time', models.DateTimeField()),
                ('count', models.IntegerField(default=0)),
                ('direction', models.CharField(max_length=200)),
                ('route', models.CharField(max_length=200)),
            ],
        ),
    ]
