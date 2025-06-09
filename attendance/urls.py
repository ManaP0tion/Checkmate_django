from django.urls import path
from .views import (
    StartAttendanceSessionView, EndAttendanceSessionView,
    StudentAttendanceStatsView, MyAttendanceRecordsView, AttendanceStatisticsView,
    AttendanceRecordCreateView, ManualAttendanceUpdateView,
    LectureCreateView, ProfessorLectureListView, LectureSessionListView,
    BLEAttendanceView, QRAttendanceView, QRCodeGenerateView,
    SessionAttendanceListView, StudentSearchView, ProfessorAttendanceSummaryView,
    RaspberryPiConnectionCheckView, MyLectureListView, WeeklyAttendanceView, LectureStudentListView
)

urlpatterns = [
    # 세션 관리
    path('sessions/start/', StartAttendanceSessionView.as_view(), name='start-attendance-session'),
    path('sessions/end/', EndAttendanceSessionView.as_view(), name='end-attendance-session'),
    path('sessions/<str:lecture_code>/list/', LectureSessionListView.as_view(), name='lecture-sessions'),
    path('sessions/<int:session_id>/attendance/', SessionAttendanceListView.as_view(), name='session-attendance-list'),

    # 강의 관련
    path('lectures/create/', LectureCreateView.as_view(), name='create-lecture'),
    path('lectures/my/', ProfessorLectureListView.as_view(), name='my-lectures'),

    # 출석 처리
    path('attendance/submit/', AttendanceRecordCreateView.as_view(), name='submit-attendance'),
    path('attendance/manual-update/', ManualAttendanceUpdateView.as_view(), name='manual-attendance-update'),

    # 출석 통계
    path('attendance/statistics/', AttendanceStatisticsView.as_view(), name='attendance-statistics'),
    path('attendance/my-records/', MyAttendanceRecordsView.as_view(), name='my-attendance-records'),
    path('attendance/stats/<str:lecture_code>/', StudentAttendanceStatsView.as_view(), name='student-attendance-stats'),
    path('attendance/summary/', ProfessorAttendanceSummaryView.as_view(), name='attendance-summary'),

    # BLE / QR 출석
    path('attendance/ble/', BLEAttendanceView.as_view(), name='ble-attendance'),
    path('attendance/qr/', QRAttendanceView.as_view(), name='qr-attendance'),
    path('attendance/qr/generate/', QRCodeGenerateView.as_view(), name='generate-qr'),
    path('raspi-check/', RaspberryPiConnectionCheckView.as_view(), name='raspi-check'),

    # 학생 검색
    path('students/search/', StudentSearchView.as_view(), name='search-students'),
    path('my-lectures/', MyLectureListView.as_view(), name='my-lecture-list'),

    path('weekly/', WeeklyAttendanceView.as_view()),  # 교수용 주차별 출석 조회
    path('my-lectures/', MyLectureListView.as_view()),

    path('lectures/students/', LectureStudentListView.as_view(), name='lecture-students')


]