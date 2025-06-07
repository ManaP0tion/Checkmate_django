from django.db import models
from users.models import User

class Lecture(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    total_weeks = models.PositiveIntegerField(default=15)
    professor = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'professor'})
    students = models.ManyToManyField(User, related_name='enrolled_lectures', limit_choices_to={'role': 'student'})

    def __str__(self):
        return f"{self.name} ({self.code})"


class AttendanceSession(models.Model):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE)
    week = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

class AttendanceRecord(models.Model):
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'})
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=[
        ('present', '출석'),
        ('late', '지각'),
        ('absent', '결석'),
    ])

    class Meta:
        unique_together = ('session', 'student')

class AttendanceChangeLog(models.Model):
    professor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="change_logs")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="changed_logs")
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE)
    old_status = models.CharField(max_length=10)
    new_status = models.CharField(max_length=10)
    changed_at = models.DateTimeField(auto_now_add=True)