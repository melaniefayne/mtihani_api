# Generated by Django 5.1.7 on 2025-03-26 15:59

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BloomSkill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('examples', models.JSONField()),
            ],
        ),
        migrations.CreateModel(
            name='Strand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('number', models.FloatField()),
                ('grade', models.IntegerField()),
            ],
            options={
                'unique_together': {('grade', 'number')},
            },
        ),
        migrations.CreateModel(
            name='SubStrand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('number', models.FloatField()),
                ('lesson_count', models.IntegerField()),
                ('descriptions', models.JSONField()),
                ('learning_outcomes', models.JSONField()),
                ('learning_experiences', models.JSONField()),
                ('key_inquiries', models.JSONField()),
                ('core_competencies', models.JSONField()),
                ('values', models.JSONField()),
                ('pertinent_issues', models.JSONField()),
                ('other_learning_areas', models.JSONField()),
                ('learning_materials', models.JSONField()),
                ('non_formal_activities', models.JSONField()),
                ('strand', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sub_strands', to='cbc.strand')),
            ],
            options={
                'unique_together': {('strand', 'number')},
            },
        ),
        migrations.CreateModel(
            name='Skill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('skill', models.CharField(max_length=255)),
                ('sub_strand', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='skills', to='cbc.substrand')),
            ],
            options={
                'unique_together': {('sub_strand', 'skill')},
            },
        ),
        migrations.CreateModel(
            name='AssessmentRubric',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('expectation', models.CharField(max_length=50)),
                ('description', models.TextField(max_length=255)),
                ('skill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rubrics', to='cbc.skill')),
            ],
            options={
                'unique_together': {('skill', 'expectation')},
            },
        ),
    ]
