import requests
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AttendanceSession, Lecture, AttendanceRecord
from .serializers import AttendanceSessionSerializer, LectureCreateSerializer

RASPBERRY_PI_URL = "http://127.0.0.1:8000/api/ble/advertise/"
RASPBERRY_PI_STOP_URL = "http://127.0.0.1:8000/api/ble/stop/"

# 출석 시작 (세션 생성)
class StartAttendanceSessionView(APIView):
    def post(self, request):
        lecture_id = request.data.get('lecture')
        week = request.data.get('week')

        if not lecture_id or not week:
            return Response({"error": "lecture와 week는 필수입니다."}, status=400)

        try:
            lecture = Lecture.objects.get(id=lecture_id)
        except Lecture.DoesNotExist:
            return Response({"error": "해당 강의를 찾을 수 없습니다."}, status=404)

        session = AttendanceSession.objects.create(
            lecture=lecture,
            week=week,
            is_active=True
        )

        # ✅ 교수 username 포함해서 전송
        payload = {
            "lecture_id": lecture.id,
            "session_id": session.id,
            "professor_username": lecture.professor.username
        }

        try:
            response = requests.post(RASPBERRY_PI_URL, json=payload, timeout=3)
            if response.status_code != 200:
                return Response({
                    "session": AttendanceSessionSerializer(session).data,
                    "warning": "세션은 생성되었지만 라즈베리파이 응답이 올바르지 않음"
                }, status=207)
        except requests.RequestException:
            return Response({
                "session": AttendanceSessionSerializer(session).data,
                "warning": "세션은 생성되었지만 라즈베리파이에 연결할 수 없음"
            }, status=207)

        return Response(AttendanceSessionSerializer(session).data, status=201)

# 출석 종료 (is_active → False)
class EndAttendanceSessionView(APIView):
    def post(self, request):
        session_id = request.data.get('session_id')

        if not session_id:
            return Response({"error": "session_id는 필수입니다."}, status=400)

        try:
            session = AttendanceSession.objects.get(id=session_id, is_active=True)
        except AttendanceSession.DoesNotExist:
            return Response({"error": "활성화된 세션을 찾을 수 없습니다."}, status=404)

        session.is_active = False
        session.save()

        # ✅ 라즈베리파이에 세션 종료 요청
        try:
            response = requests.post(RASPBERRY_PI_STOP_URL, json={"session_id": session.id}, timeout=3)
            if response.status_code != 200:
                return Response({
                    "session": AttendanceSessionSerializer(session).data,
                    "warning": "세션은 종료되었지만 라즈베리파이 응답이 올바르지 않음"
                }, status=207)
        except requests.RequestException:
            return Response({
                "session": AttendanceSessionSerializer(session).data,
                "warning": "세션은 종료되었지만 라즈베리파이에 연결할 수 없음"
            }, status=207)

        return Response(AttendanceSessionSerializer(session).data, status=200)

# 출석통계 API
class StudentAttendanceStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lecture_id):
        user = request.user

        try:
            lecture = Lecture.objects.get(id=lecture_id)
        except Lecture.DoesNotExist:
            return Response({"error": "강의를 찾을 수 없습니다."}, status=404)

        # 해당 강의의 출석 기록 필터
        records = AttendanceRecord.objects.filter(
            student=user,
            session__lecture=lecture
        )

        total_weeks = lecture.total_weeks
        attended = records.filter(status="present").count()
        late = records.filter(status="late").count()
        absent = records.filter(status="absent").count()
        total_recorded = attended + late + absent

        rate = (attended + late * 0.5) / total_weeks * 100 if total_weeks > 0 else 0

        return Response({
            "lecture": lecture.name,
            "total_weeks": total_weeks,
            "attended": attended,
            "late": late,
            "absent": absent,
            "attendance_rate": round(rate, 1)
        })

class LectureCreateView(generics.CreateAPIView):
    queryset = Lecture.objects.all()
    serializer_class = LectureCreateSerializer
    permission_classes = [IsAdminUser]  # 관리자만 등록 가능