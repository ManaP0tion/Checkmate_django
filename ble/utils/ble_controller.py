import time
from datetime import datetime

def start_ble_advertising(lecture_id, session_id, professor_username):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [BLE START] 광고 시작됨")
    print(f"  - 강의 ID: {lecture_id}")
    print(f"  - 세션 ID: {session_id}")
    print(f"  - 교수 Username: {professor_username}")

    # 실제 BLE 광고 로직은 여기 들어가야 함
    # 예시용으로 1초 대기
    time.sleep(1)

def stop_ble_advertising(session_id):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [BLE STOP] 광고 종료됨")
    print(f"  - 세션 ID: {session_id}")

    # 실제 BLE 종료 로직은 여기 들어가야 함
    time.sleep(1)