# ble/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

@api_view(['POST'])
def mock_advertise(request):
    lecture_id = request.data.get('lecture_id')
    session_id = request.data.get('session_id')
    professor_username = request.data.get('professor_username')

    print(f"[BLE 광고 시작] 강의 ID: {lecture_id}, 세션 ID: {session_id}, 교수: {professor_username}")
    return Response({"message": "BLE 광고 시작됨 (Mock)"}, status=status.HTTP_200_OK)

@api_view(['POST'])
def mock_stop_session(request):
    session_id = request.data.get('session_id')

    print(f"[BLE 종료] 세션 ID: {session_id}")
    return Response({"message": "BLE 광고 종료됨 (Mock)"}, status=status.HTTP_200_OK)