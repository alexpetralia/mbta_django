# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-01-17 22:36
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scraper', '0004_currtrips'),
    ]

    operations = [
        migrations.CreateModel(
            name='apiStatus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.IntegerField(default=0)),
            ],
        ),
        migrations.DeleteModel(
            name='CurrTrips',
        ),
    ]
