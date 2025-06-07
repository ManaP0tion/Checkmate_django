from rest_framework import serializers
from users.models import User
from .models import AttendanceSession, Lecture, AttendanceRecord


class AttendanceSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceSession
        fields = ['id', 'lecture', 'week', 'created_at', 'is_active']
        read_only_fields = ['created_at']


class LectureCreateSerializer(serializers.ModelSerializer):
    professor_username = serializers.CharField(write_only=True)

    class Meta:
        model = Lecture
        fields = ['name', 'code', 'total_weeks', 'professor_username']

    def create(self, validated_data):
        professor_username = validated_data.pop('professor_username')
        try:
            professor = User.objects.get(username=professor_username, role='professor')
        except User.DoesNotExist:
            raise serializers.ValidationError("교수 사용자를 찾을 수 없습니다.")
        return Lecture.objects.create(professor=professor, **validated_data)


class LectureSerializer(serializers.ModelSerializer):
    professor_name = serializers.CharField(source='professor.name', read_only=True)
    students = serializers.SerializerMethodField()

    class Meta:
        model = Lecture
        fields = ['id', 'name', 'code', 'total_weeks', 'professor_name', 'students']

    def get_students(self, obj):
        return [{"id": s.id, "name": s.name} for s in obj.students.all()]


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = ['id', 'student', 'student_name', 'status', 'timestamp']