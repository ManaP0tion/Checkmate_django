from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime

# ✅ 라즈베리파이 BLE 컨트롤러 함수 임포트
from ble.utils.ble_controller import start_ble_advertising, stop_ble_advertising

@api_view(['POST'])
def mock_advertise(request):
    lecture_id = request.data.get('lecture_id')
    session_id = request.data.get('session_id')
    professor_username = request.data.get('professor_username')

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n[BLE 광고 시작 요청] {timestamp}")
    print(f"  - 강의 ID: {lecture_id}")
    print(f"  - 세션 ID: {session_id}")
    print(f"  - 교수 username: {professor_username}")

    try:
        # ✅ 실제 BLE 광고 시작 함수 호출
        start_ble_advertising(lecture_id, session_id, professor_username)
        print("  ✅ BLE 광고 성공\n")
        return Response({"message": "BLE 광고 시작됨"}, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"  ❌ BLE 광고 실패: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def mock_stop_session(request):
    session_id = request.data.get('session_id')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n[BLE 광고 종료 요청] {timestamp}")
    print(f"  - 세션 ID: {session_id}")

    try:
        # ✅ 실제 BLE 광고 종료 함수 호출
        stop_ble_advertising(session_id)
        print("  ✅ BLE 종료 성공\n")
        return Response({"message": "BLE 광고 종료됨"}, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"  ❌ BLE 종료 실패: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)