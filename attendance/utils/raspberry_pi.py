import requests

def notify_raspberry_pi_start(session):
    from attendance.serializers import AttendanceSessionSerializer
    payload = {
        "lecture_id": session.lecture.id,
        "session_id": session.id,
        "professor_username": session.lecture.professor.username
    }
    try:
        response = requests.post("http://127.0.0.1:8000/api/ble/advertise/", json=payload, timeout=3)
        return response.status_code == 200
    except requests.RequestException:
        return False

def notify_raspberry_pi_stop(session_id):
    try:
        response = requests.post("http://127.0.0.1:8000/api/ble/stop/", json={"session_id": session_id}, timeout=3)
        return response.status_code == 200
    except requests.RequestException:
        return False
