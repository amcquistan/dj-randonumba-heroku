# Generated by Django 3.1.2 on 2020-10-02 13:36

import django.contrib.postgres.fields.hstore
from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='randonumba',
            name='quote',
            field=django.contrib.postgres.fields.hstore.HStoreField(blank=True, null=True),
        ),
    ]
