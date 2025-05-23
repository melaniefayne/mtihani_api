# Generated by Django 5.1.7 on 2025-05-13 11:54

import django.db.models.deletion
import utils
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('learner', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Exam',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date_time', models.DateTimeField()),
                ('end_date_time', models.DateTimeField()),
                ('status', models.CharField(choices=[('Generating', 'Generating'), ('Failed', 'Failed'), ('Upcoming', 'Upcoming'), ('Ongoing', 'Ongoing'), ('Grading', 'Grading'), ('Complete', 'Complete'), ('Analysing', 'Analysing'), ('Archive', 'Archive')], default='Generating', max_length=25)),
                ('code', models.CharField(default=utils.generate_unique_code, max_length=50, unique=True)),
                ('duration_min', models.IntegerField(blank=True)),
                ('is_published', models.BooleanField(default=False)),
                ('is_grading', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('generation_config', models.TextField(blank=True, null=True)),
                ('generation_error', models.TextField(blank=True, null=True)),
                ('classroom', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exams', to='learner.classroom')),
                ('teacher', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='exams', to='learner.teacher')),
            ],
        ),
        migrations.CreateModel(
            name='ClassExamPerformance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('avg_score', models.FloatField()),
                ('avg_expectation_level', models.CharField(blank=True, max_length=100)),
                ('bloom_skill_scores', models.TextField(blank=True)),
                ('strand_scores', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('classroom', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='class_exam_performance', to='learner.classroom')),
                ('exam', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='exam.exam')),
            ],
        ),
        migrations.CreateModel(
            name='ExamQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.IntegerField()),
                ('grade', models.IntegerField()),
                ('strand', models.CharField(max_length=100)),
                ('sub_strand', models.CharField(max_length=100)),
                ('bloom_skill', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('expected_answer', models.TextField()),
                ('bloom_skill_options', models.TextField(blank=True)),
                ('question_options', models.TextField(blank=True)),
                ('answer_options', models.TextField(blank=True)),
                ('tr_description', models.TextField(blank=True, null=True)),
                ('tr_expected_answer', models.TextField(blank=True, null=True)),
                ('exam', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='exam.exam')),
            ],
        ),
        migrations.CreateModel(
            name='ExamQuestionAnalysis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question_count', models.IntegerField()),
                ('grade_distribution', models.TextField(blank=True)),
                ('bloom_skill_distribution', models.TextField(blank=True)),
                ('strand_distribution', models.TextField(blank=True)),
                ('sub_strand_distribution', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('exam', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='analysis', to='exam.exam')),
            ],
        ),
        migrations.CreateModel(
            name='StudentExamSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('Generating', 'Generating'), ('Failed', 'Failed'), ('Upcoming', 'Upcoming'), ('Ongoing', 'Ongoing'), ('Grading', 'Grading'), ('Complete', 'Complete'), ('Analysing', 'Analysing'), ('Archive', 'Archive')], default='Upcoming', max_length=15)),
                ('is_late_submission', models.BooleanField(default=False)),
                ('start_date_time', models.DateTimeField(null=True)),
                ('end_date_time', models.DateTimeField(blank=True, null=True)),
                ('duration_min', models.IntegerField(blank=True, null=True)),
                ('avg_score', models.FloatField(blank=True, null=True)),
                ('expectation_level', models.CharField(blank=True, max_length=100, null=True)),
                ('exam', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='exam.exam')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='student_exam_session', to='learner.student')),
            ],
            options={
                'unique_together': {('student', 'exam')},
            },
        ),
        migrations.CreateModel(
            name='StudentExamSessionAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.TextField()),
                ('score', models.FloatField(blank=True, null=True)),
                ('tr_score', models.FloatField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='exam.examquestion')),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='exam.studentexamsession')),
            ],
        ),
        migrations.CreateModel(
            name='StudentExamSessionPerformance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('avg_score', models.FloatField()),
                ('avg_expectation_level', models.CharField(blank=True, max_length=100)),
                ('bloom_skill_scores', models.TextField(blank=True)),
                ('strand_scores', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('session', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='student_exam_session_performance', to='exam.studentexamsession')),
            ],
        ),
    ]
