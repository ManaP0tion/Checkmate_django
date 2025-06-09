import requests
from django.http import HttpResponse
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

import qrcode
print("QR module loaded from:", qrcode.__file__)
import base64
from io import BytesIO

from users.models import User
from .models import AttendanceSession, Lecture, AttendanceRecord
from .serializers import (
    AttendanceSessionSerializer,
    LectureCreateSerializer,
    LectureSerializer,
    AttendanceRecordSerializer
)
from .utils.raspberry_pi import notify_raspberry_pi_start, notify_raspberry_pi_stop, check_raspberry_pi_connection


# 출석 시작 (세션 생성)
class StartAttendanceSessionView(APIView):
    @swagger_auto_schema(
        operation_summary="출석 세션 시작",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["lecture_code", "week"],
            properties={
                "lecture_code": openapi.Schema(type=openapi.TYPE_STRING, description="강의 코드"),
                "week": openapi.Schema(type=openapi.TYPE_INTEGER, description="주차"),
            }
        )
    )
    def post(self, request):
        lecture_code = request.data.get('lecture_code')
        week = request.data.get('week')

        if not lecture_code or not week:
            return Response({"error": "lecture_code와 week는 필수입니다."}, status=400)

        try:
            lecture = Lecture.objects.get(code=lecture_code)
        except Lecture.DoesNotExist:
            return Response({"error": "해당 강의를 찾을 수 없습니다."}, status=404)

        session = AttendanceSession.objects.create(
            lecture=lecture,
            week=week,
            is_active=True
        )

        # ✅ 교수 username 포함해서 전송
        success = notify_raspberry_pi_start(session)
        if not success:
            return Response({
                "session": AttendanceSessionSerializer(session).data,
                "warning": "세션은 생성되었지만 라즈베리파이에 연결할 수 없음"
            }, status=207)
        return Response(AttendanceSessionSerializer(session).data, status=201)

# 출석 종료 (is_active → False)
class EndAttendanceSessionView(APIView):
    @swagger_auto_schema(
        operation_summary="출석 세션 종료",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["session_id"],
            properties={
                "session_id": openapi.Schema(type=openapi.TYPE_STRING, description="세션 ID"),
            }
        )
    )
    def post(self, request):
        session_id = str(request.data.get('session_id'))

        if not session_id:
            return Response({"error": "session_id는 필수입니다."}, status=400)

        try:
            session = AttendanceSession.objects.get(session_code=session_id, is_active=True)
        except AttendanceSession.DoesNotExist:
            return Response({"error": "활성화된 세션을 찾을 수 없습니다."}, status=404)

        session.is_active = False
        session.save()

        success = notify_raspberry_pi_stop(session.id)
        if not success:
            return Response({
                "session": AttendanceSessionSerializer(session).data,
                "warning": "세션은 종료되었지만 라즈베리파이에 연결할 수 없음"
            }, status=207)
        return Response(AttendanceSessionSerializer(session).data, status=200)

# 출석통계 API
class StudentAttendanceStatsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'lecture_code',
                openapi.IN_PATH,
                description="강의 코드",
                type=openapi.TYPE_STRING,
                required=True
            )
        ]
    )
    def get(self, request, lecture_code):
        user = request.user

        try:
            lecture = Lecture.objects.get(code=lecture_code)
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

    @swagger_auto_schema(
        operation_summary="학생 출석 제출",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["session_code"],
            properties={
                "session_code": openapi.Schema(type=openapi.TYPE_STRING, description="세션 코드 (예: CS101_2)"),
                "status": openapi.Schema(type=openapi.TYPE_STRING, description="출석 상태", enum=["present", "late", "absent"]),
            }
        )
    )
    def post(self, request):
        user = request.user  # JWT 인증된 사용자
        session_code = request.data.get('session_code')
        status_value = request.data.get('status', 'present')  # 기본값은 출석

        # 1. 사용자 권한 확인
        if user.role != 'student':
            return Response({"error": "학생만 출석할 수 있습니다."}, status=403)

        # 2. 세션 유효성 확인
        if not session_code:
            return Response({"error": "session_code는 필수입니다."}, status=400)

        try:
            session = AttendanceSession.objects.get(session_code=session_code, is_active=True)
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
            'lecture_code',
            openapi.IN_QUERY,
            description="강의 코드",
            type=openapi.TYPE_STRING,
            required=True
        )
    ])

    def get(self, request):
        lecture_code = request.query_params.get('lecture_code')
        if not lecture_code:
            return Response({"error": "lecture_code는 필수입니다."}, status=400)

        try:
            lecture = Lecture.objects.get(code=lecture_code)
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


class MyAttendanceRecordsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter(
            'lecture_code',
            openapi.IN_QUERY,
            description="강의 코드",
            type=openapi.TYPE_STRING,
            required=True
        )
    ])
    def get(self, request):
        user = request.user
        lecture_code = request.query_params.get('lecture_code')

        if user.role != 'student':
            return Response({"error": "학생만 접근할 수 있습니다."}, status=403)

        if not lecture_code:
            return Response({"error": "lecture_code는 필수입니다."}, status=400)

        try:
            lecture = Lecture.objects.get(code=lecture_code)
        except Lecture.DoesNotExist:
            return Response({"error": "강의를 찾을 수 없습니다."}, status=404)

        records = AttendanceRecord.objects.filter(student=user, session__lecture=lecture)

        data = []
        for record in records.order_by('session__week'):
            data.append({
                "week": record.session.week,
                "status": record.status
            })

        return Response({
            "lecture": lecture.name,
            "student": user.name,
            "records": data
        })

class ManualAttendanceUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="출석 수동 수정 (교수 전용)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['lecture_code', 'week', 'student_username', 'status'],
            properties={
                'lecture_code': openapi.Schema(type=openapi.TYPE_STRING, description='강의 코드'),
                'week': openapi.Schema(type=openapi.TYPE_INTEGER, description='주차'),
                'student_username': openapi.Schema(type=openapi.TYPE_STRING, description='학생 학번 (username)'),
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='출석 상태 (present, late, absent)',
                    enum=['present', 'late', 'absent']
                ),
            }
        ),
        responses={
            200: openapi.Response(description="출석 상태 수정 완료"),
            400: "잘못된 요청",
            403: "권한 없음",
            404: "데이터 없음"
        }
    )
    def post(self, request):
        lecture_code = request.data.get('lecture_code')
        week = request.data.get('week')
        student_username = request.data.get('student_username')
        status_value = request.data.get('status')

        if not lecture_code or not week or not student_username or not status_value:
            return Response({"error": "lecture_code, week, student_username, status는 필수입니다."}, status=400)

        try:
            lecture = Lecture.objects.get(code=lecture_code, professor=request.user)
            session = AttendanceSession.objects.get(lecture=lecture, week=week)
        except Lecture.DoesNotExist:
            return Response({"error": "해당 강의를 찾을 수 없습니다."}, status=404)
        except AttendanceSession.DoesNotExist:
            return Response({"error": "해당 강의의 해당 주차 세션이 존재하지 않습니다."}, status=404)

        if session.lecture.professor != request.user:
            return Response({"error": "해당 세션에 대한 수정 권한이 없습니다."}, status=403)

        try:
            student = User.objects.get(username=student_username, role='student')
        except User.DoesNotExist:
            return Response({"error": "학생 정보를 찾을 수 없습니다."}, status=404)

        if not session.lecture.students.filter(id=student.id).exists():
            return Response({"error": "해당 학생은 이 강의를 수강하지 않습니다."}, status=403)

        record, created = AttendanceRecord.objects.get_or_create(
            session=session,
            student=student,
            defaults={'status': status_value}
        )
        if not created and record.status != status_value:
            from .models import AttendanceChangeLog
            AttendanceChangeLog.objects.create(
                professor=request.user,
                student=student,
                session=session,
                old_status=record.status,
                new_status=status_value
            )
            record.status = status_value
            record.save()

        return Response({
            "message": "출석 상태 수정 완료" if not created else "출석 기록 생성 및 설정 완료",
            "lecture": session.lecture.name,
            "week": session.week,
            "student": student.name,
            "status": status_value
        }, status=200)



class ProfessorLectureListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(operation_summary="교수의 강의 목록 조회")
    def get(self, request):
        professor = request.user
        if professor.role != 'professor':
            return Response({"error": "접근 권한이 없습니다."}, status=403)

        lectures = Lecture.objects.filter(professor=professor)
        serializer = LectureSerializer(lectures, many=True)
        return Response(serializer.data)

class LectureSessionListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="해당 강의의 세션 목록 조회",
        manual_parameters=[
            openapi.Parameter(
                'lecture_code',
                openapi.IN_PATH,
                description="강의 코드",
                type=openapi.TYPE_STRING,
                required=True
            )
        ]
    )
    def get(self, request, lecture_code):
        professor = request.user
        try:
            lecture = Lecture.objects.get(code=lecture_code, professor=professor)
        except Lecture.DoesNotExist:
            return Response({"error": "해당 강의가 없거나 권한이 없습니다."}, status=404)

        sessions = AttendanceSession.objects.filter(lecture=lecture)
        serializer = AttendanceSessionSerializer(sessions, many=True)
        return Response(serializer.data)


# 학생 이름 검색 API
class StudentSearchView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter('name', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="학생 이름 검색"),
        openapi.Parameter('lecture_code', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="강의 코드", required=True),
    ])
    def get(self, request):
        name = request.query_params.get('name', '')
        lecture_code = request.query_params.get('lecture_code')

        try:
            lecture = Lecture.objects.get(code=lecture_code, professor=request.user)
        except Lecture.DoesNotExist:
            return Response({"error": "강의를 찾을 수 없습니다."}, status=404)

        students = lecture.students.filter(name__icontains=name)
        return Response([{"id": s.id, "name": s.name} for s in students])


# 교수 출석 요약 통계 API
class ProfessorAttendanceSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="교수용 출석 요약 통계 API",
        manual_parameters=[]
    )
    def get(self, request):
        professor = request.user
        if professor.role != 'professor':
            return Response({"error": "접근 권한이 없습니다."}, status=403)

        data = []
        lectures = Lecture.objects.filter(professor=professor)

        for lecture in lectures:
            total_weeks = lecture.total_weeks
            total_students = lecture.students.count()
            total_records = AttendanceRecord.objects.filter(session__lecture=lecture)

            present = total_records.filter(status='present').count()
            late = total_records.filter(status='late').count()
            absent = total_records.filter(status='absent').count()
            total = total_students * total_weeks

            rate = round((present + late * 0.5) / total * 100, 1) if total else 0

            data.append({
                "lecture": lecture.name,
                "출석률": rate,
                "출석": present,
                "지각": late,
                "결석": absent,
                "총 학생": total_students,
                "총 주차": total_weeks
            })

        return Response(data)


class SessionAttendanceListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter(
            'session_id',
            openapi.IN_PATH,
            description="세션 ID",
            type=openapi.TYPE_INTEGER,
            required=True
        )
    ])

    def get(self, request, session_id):
        professor = request.user

        try:
            session = AttendanceSession.objects.get(id=session_id)
        except AttendanceSession.DoesNotExist:
            return Response({"error": "세션을 찾을 수 없습니다."}, status=404)

        if session.lecture.professor != professor:
            return Response({"error": "해당 세션에 접근할 수 없습니다."}, status=403)

        records = AttendanceRecord.objects.filter(session=session)
        serializer = AttendanceRecordSerializer(records, many=True)
        return Response(serializer.data)


# BLE 응답 출석 처리
class BLEAttendanceView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="BLE 출석 처리",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["student_id", "lecture_code", "session_id"],
            properties={
                "student_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "lecture_code": openapi.Schema(type=openapi.TYPE_STRING),
                "session_id": openapi.Schema(type=openapi.TYPE_INTEGER),
            }
        )
    )
    def post(self, request):
        student_id = request.data.get("student_id")
        lecture_code = request.data.get("lecture_code")
        session_id = request.data.get("session_id")

        try:
            student = User.objects.get(id=student_id)
            session = AttendanceSession.objects.get(id=session_id, lecture__code=lecture_code)
        except (User.DoesNotExist, AttendanceSession.DoesNotExist):
            return Response({"error": "학생 또는 세션을 찾을 수 없습니다."}, status=404)

        if not session.lecture.students.filter(id=student.id).exists():
            return Response({"error": "수강하지 않는 학생입니다."}, status=403)

        record, created = AttendanceRecord.objects.get_or_create(
            session=session,
            student=student,
            defaults={"status": "present"}
        )

        return Response({"message": "BLE 출석 완료" if created else "이미 출석 처리됨"})


# QR 스캔 출석 처리
class QRAttendanceView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="QR 출석 처리",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["session_id"],
            properties={
                "session_id": openapi.Schema(type=openapi.TYPE_STRING, description="세션 코드 (예: CS101_2)"),
            }
        )
    )
    def post(self, request):
        user = request.user
        session_id = str(request.data.get("session_id"))

        try:
            session = AttendanceSession.objects.get(session_code=session_id)
        except AttendanceSession.DoesNotExist:
            return Response({"error": "세션을 찾을 수 없습니다."}, status=404)

        if not session.lecture.students.filter(id=user.id).exists():
            return Response({"error": "수강하지 않는 학생입니다."}, status=403)

        record, created = AttendanceRecord.objects.get_or_create(
            session=session,
            student=user,
            defaults={"status": "present"}
        )

        return Response({"message": "QR 출석 완료" if created else "이미 출석 처리됨"})


# QR 코드 생성 뷰
class QRCodeGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="QR 코드 생성",
        manual_parameters=[
            openapi.Parameter(
                "session_id", openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="세션 ID"
            )
        ]
    )
    def get(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response({"error": "session_id는 필수입니다."}, status=400)
        session_id = str(session_id)

        qr = qrcode.make(f"checkmate://attendance?session_id={session_id}")
        buffered = BytesIO()
        qr.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode()

        return Response({"qr_image_base64": qr_base64})


class RaspberryPiConnectionCheckView(APIView):
    def get(self, request):
        try:
            response = requests.get("http://192.168.137.119:5000/ping", timeout=2)
            if response.status_code == 200:
                return Response({"connected": True})
        except requests.RequestException:
            return Response({"connected": False})

# 교수용: 주차별 전체 학생 출결 조회 API
class WeeklyAttendanceView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="주차별 전체 학생 출결 조회",
        manual_parameters=[
            openapi.Parameter('lecture_code', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True, description="강의 코드"),
            openapi.Parameter('week', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True, description="주차"),
        ]
    )
    def get(self, request):
        professor = request.user
        lecture_code = request.query_params.get("lecture_code")
        week = request.query_params.get("week")

        if professor.role != 'professor':
            return Response({"error": "접근 권한이 없습니다."}, status=403)

        if not lecture_code or not week:
            return Response({"error": "lecture_code와 week는 필수입니다."}, status=400)

        try:
            lecture = Lecture.objects.get(code=lecture_code, professor=professor)
        except Lecture.DoesNotExist:
            return Response({"error": "강의를 찾을 수 없습니다."}, status=404)

        try:
            session = AttendanceSession.objects.get(lecture=lecture, week=week)
        except AttendanceSession.DoesNotExist:
            return Response({"error": "해당 주차의 세션이 존재하지 않습니다."}, status=404)

        results = []
        for student in lecture.students.all():
            record, created = AttendanceRecord.objects.get_or_create(
                session=session,
                student=student,
                defaults={"status": "absent"}
            )
            results.append({
                "student_id": student.id,
                "student_name": student.name,
                "status": record.status
            })

        return Response({
            "lecture": lecture.name,
            "week": week,
            "records": results
        })


# 학생용: 내 수강 강의 리스트 조회
class MyLectureListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(operation_summary="학생의 수강 강의 목록 조회")
    def get(self, request):
        user = request.user
        if user.role != 'student':
            return Response({"error": "학생만 접근 가능합니다."}, status=403)

        lectures = Lecture.objects.filter(students=user)
        return Response([
            {
                "lecture_id": l.id,
                "lecture_code": l.code, # 코드도 받도록 반영
                "name": l.name,
                "professor": l.professor.name
            } for l in lectures
        ])

# 특정강의 수강학생 조회 API
class LectureStudentListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="특정 강의 수강 학생 목록 조회",
        manual_parameters=[
            openapi.Parameter('lecture_code', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True, description="강의 코드"),
        ]
    )
    def get(self, request):
        professor = request.user
        lecture_code = request.query_params.get("lecture_code")

        if not lecture_code:
            return Response({"error": "lecture_code는 필수입니다."}, status=400)

        try:
            lecture = Lecture.objects.get(code=lecture_code, professor=professor)
        except Lecture.DoesNotExist:
            return Response({"error": "해당 강의를 찾을 수 없습니다."}, status=404)

        students = lecture.students.all()
        return Response([
            {
                "id": s.id,
                "username": s.username,
                "name": s.name,
                "major": s.major,
                "department": s.department,
            } for s in students
        ])

def qr_image_view(request):
    session_code = request.GET.get("session_code")
    if not session_code:
        return HttpResponse("session_code 파라미터가 필요합니다.", status=400)

    # QR 생성
    qr = qrcode.make(f"checkmate://attendance?session_code={session_code}")
    buffer = BytesIO()
    qr.save(buffer, format="PNG")

    # 이미지 응답
    return HttpResponse(buffer.getvalue(), content_type="image/png")
