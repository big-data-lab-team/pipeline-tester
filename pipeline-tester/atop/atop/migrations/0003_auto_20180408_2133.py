# Generated by Django 2.0.2 on 2018-04-09 01:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('atop', '0002_auto_20180403_0629'),
    ]

    operations = [
        migrations.CreateModel(
            name='CarminPlatform',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('root_url', models.URLField(default='')),
                ('api_key', models.CharField(max_length=100)),
            ],
        ),
        migrations.AddField(
            model_name='descriptor',
            name='carmin_platform',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='atop.CarminPlatform'),
        ),
    ]
