# Generated by Django 2.2.19 on 2021-11-05 18:03

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0003_auto_20211105_1950'),
    ]

    operations = [
        migrations.AlterField(
            model_name='post',
            name='group',
            field=models.ForeignKey(blank=True, max_length=200, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='group', to='posts.Group'),
        ),
    ]