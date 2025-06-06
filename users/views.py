from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics

from .models import User
from .serializers import LoginSerializer, RegisterSerializer

class LoginAPIView(APIView):

    @swagger_auto_schema(request_body=LoginSerializer)  # ✅ Swagger용 추가
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user_id': user.id,
                'role': user.role,
                'name': user.name
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class RegisterAPIView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["username", "email", "password", "role", "name"],
            properties={
                "username": openapi.Schema(type=openapi.TYPE_STRING, example="20241234"),
                "email": openapi.Schema(type=openapi.TYPE_STRING, format="email", example="student@example.com"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, format="password", example="abcd1234"),
                "role": openapi.Schema(type=openapi.TYPE_STRING, example="student"),
                "name": openapi.Schema(type=openapi.TYPE_STRING, example="홍길동"),
                "major": openapi.Schema(type=openapi.TYPE_STRING, example="컴퓨터공학"),
                "department": openapi.Schema(type=openapi.TYPE_STRING, example="")  # 학생은 공백
            },
        ),
        operation_summary="회원가입 API",
        operation_description="학생 또는 교수로 회원가입합니다. 역할에 따라 major 또는 department는 필수입니다."
    )

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
