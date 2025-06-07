import requests
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User
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

class AttendanceRecordCreateView(APIView):
    """
    학생 출석 제출 API
    - 인증된 학생만 출석 가능
    - 세션 ID를 통해 활성 세션 확인
    - 해당 학생이 수강 중인지 검증 후 출석 처리
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user  # JWT 인증된 사용자
        session_id = request.data.get('session_id')
        status_value = request.data.get('status', 'present')  # 기본값은 출석

        # 1. 사용자 권한 확인
        if user.role != 'student':
            return Response({"error": "학생만 출석할 수 있습니다."}, status=403)

        # 2. 세션 유효성 확인
        if not session_id:
            return Response({"error": "session_id는 필수입니다."}, status=400)

        try:
            session = AttendanceSession.objects.get(id=session_id, is_active=True)
        except AttendanceSession.DoesNotExist:
            return Response({"error": "활성화된 출석 세션이 존재하지 않습니다."}, status=404)

        # 3. 수강 여부 확인
        if not session.lecture.students.filter(id=user.id).exists():
            return Response({"error": "해당 강의를 수강하지 않습니다."}, status=403)

        # 4. 출석 기록 생성 또는 확인
        record, created = AttendanceRecord.objects.get_or_create(
            session=session,
            student=user,
            defaults={'status': status_value}
        )

        return Response({
            "message": "출석 완료" if created else "이미 출석 처리됨",
            "data": {
                "session": session.id,
                "student": user.name,
                "status": status_value
            }
        }, status=200)

class AttendanceStatisticsView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter(
            'lecture_id',
            openapi.IN_QUERY,
            description="강의 ID",
            type=openapi.TYPE_INTEGER,
            required=True
        )
    ])

    def get(self, request):
        lecture_id = request.query_params.get('lecture_id')
        if not lecture_id:
            return Response({"error": "lecture_id는 필수입니다."}, status=400)

        try:
            lecture = Lecture.objects.get(id=lecture_id)
        except Lecture.DoesNotExist:
            return Response({"error": "강의를 찾을 수 없습니다."}, status=404)

        total_weeks = lecture.total_weeks
        data = {
            "lecture": lecture.name,
            "total_weeks": total_weeks,
            "students": []
        }

        for student in lecture.students.all():
            records = AttendanceRecord.objects.filter(student=student, session__lecture=lecture)
            present = records.filter(status='출석').count()
            late = records.filter(status='지각').count()
            absent = records.filter(status='결석').count()
            total = present + late + absent

            attendance_rate = round((present + late * 0.5) / total_weeks * 100, 1) if total_weeks else 0

            data["students"].append({
                "student_id": student.id,
                "name": student.name,
                "출석": present,
                "지각": late,
                "결석": absent,
                "출석률": attendance_rate
            })

        return Response(data)