from rest_framework import serializers
from .models import AttendanceSession, Lecture


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