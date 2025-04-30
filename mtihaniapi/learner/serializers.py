# learner/serializers.py
from rest_framework import serializers

from learner.models import Classroom, LessonTime, ClassroomStudent, TermScore


class TermScoreInputSerializer(serializers.Serializer):
    grade = serializers.IntegerField()
    term = serializers.IntegerField()
    score = serializers.FloatField()


class UploadedStudentSerializer(serializers.Serializer):
    name = serializers.CharField()
    scores = TermScoreInputSerializer(many=True)


class LessonTimeSerializer(serializers.Serializer):
    day = serializers.ChoiceField(
        choices=[day[0] for day in LessonTime.WEEKDAYS])
    time = serializers.TimeField(format='%H:%M', input_formats=['%H:%M'])

    def validate_day(self, value):
        if value not in dict(LessonTime.WEEKDAYS):
            raise serializers.ValidationError("Invalid weekday.")
        return value

    def validate(self, data):
        day = data.get('day')
        time = data.get('time')
        classroom = self.context.get('classroom')

        if classroom and LessonTime.objects.filter(classroom=classroom, day=day, time=time).exists():
            raise serializers.ValidationError("Lesson time already exists for this day and time.")
        return data


class ClassroomSerializer(serializers.ModelSerializer):
    lesson_times = LessonTimeSerializer(many=True, write_only=True)
    uploaded_students = UploadedStudentSerializer(
        many=True, required=False, write_only=True)

    class Meta:
        model = Classroom
        fields = [
            'name', 'grade', 'subject', 'school_name', 'school_address',
            'lesson_times', 'uploaded_students'
        ]

    def create(self, validated_data):
        lesson_times_data = validated_data.pop('lesson_times', [])
        uploaded_students = validated_data.pop('uploaded_students', [])
        teacher = self.context['request'].user.teacher

        classroom = Classroom.objects.create(teacher=teacher, **validated_data)

        # Create lesson times
        for lt in lesson_times_data:
            LessonTime.objects.create(classroom=classroom, **lt)

        # Create students + term scores
        for student_data in uploaded_students:
            student_name = student_data['name']
            term_scores_data = student_data.get('scores', [])

            existing = classroom.students.filter(name=student_name).exists()
            if existing:
                raise serializers.ValidationError(
                    f"A student named '{student_name}' already exists in this classroom.")

            classroom_student = ClassroomStudent.objects.create(name=student_name)
            classroom_student.classroom.add(classroom)

            for score_data in term_scores_data:
                TermScore.objects.create(
                    classroom_student=classroom_student,
                    **score_data
                )

        return classroom


class TermScoreSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    grade = serializers.IntegerField()
    term = serializers.IntegerField()
    score = serializers.FloatField()
    expectation_level = serializers.CharField()


class ClassroomDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    grade = serializers.IntegerField()
    subject = serializers.CharField()
    school_name = serializers.CharField()
    school_address = serializers.CharField()
    teacher_id = serializers.IntegerField(allow_null=True)
    lesson_times = serializers.ListField(child=serializers.CharField())
    avg_term_score = serializers.FloatField()
    avg_term_expectation_level = serializers.CharField()
    avg_mtihani_score = serializers.FloatField()
    avg_mtihani_expectation_level = serializers.CharField()

    # Optional for teachers
    student_count = serializers.IntegerField(required=False)

    # Optional for students
    student_code = serializers.CharField(required=False)
    term_scores = TermScoreSerializer(many=True, required=False)
