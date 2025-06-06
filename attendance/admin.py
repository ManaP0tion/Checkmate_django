from django.contrib import admin
from .models import Lecture, AttendanceSession, AttendanceRecord

@admin.register(Lecture)
class LectureAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'professor', 'total_weeks')
    search_fields = ('name', 'code', 'professor__name')
    filter_horizontal = ('students',)

@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ('lecture', 'week', 'is_active')

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('session', 'student', 'status', 'timestamp')
    list_filter = ('status',)