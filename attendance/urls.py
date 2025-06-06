from django.urls import path
from .views import StartAttendanceSessionView, EndAttendanceSessionView, StudentAttendanceStatsView, LectureCreateView, \
    AttendanceRecordCreateView

urlpatterns = [
    path('start-session/', StartAttendanceSessionView.as_view(), name='start_attendance_session'),
    path('end-session/', EndAttendanceSessionView.as_view(), name='end_attendance_session'),
    path("stats/<int:lecture_id>/", StudentAttendanceStatsView.as_view(), name="student_attendance_stats"),
    path('create-lecture/', LectureCreateView.as_view(), name='create-lecture'),
    path('submit-attendance/', AttendanceRecordCreateView.as_view(), name='submit-attendance'),
]