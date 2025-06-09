import requests

RASPBERRY_PI_IP = "192.168.137.119"
RASPBERRY_PI_PORT = 5000

def notify_raspberry_pi_start(session):
    session_code = f"{session.lecture.code}_{session.week}"
    payload = {
        "session_id": session_code,
        "professor_username": session.lecture.professor.username
    }
    try:
        response = requests.post(
            f"http://{RASPBERRY_PI_IP}:{RASPBERRY_PI_PORT}/api/ble/advertise/",
            json=payload,
            timeout=3
        )
        return response.status_code == 200
    except requests.RequestException:
        return False

def notify_raspberry_pi_stop(session):
    session_code = f"{session.lecture.code}_{session.week}"
    try:
        response = requests.post(
            f"http://{RASPBERRY_PI_IP}:{RASPBERRY_PI_PORT}/api/ble/stop/",
            json={"session_id": session_code},
            timeout=3
        )
        return response.status_code == 200
    except requests.RequestException:
        return False

def check_raspberry_pi_connection():
    try:
        response = requests.get("http://192.168.137.119:5000/ping", timeout=2)
        return response.status_code == 200 and response.json().get('message') == 'pong'
    except requests.RequestException:
        return False