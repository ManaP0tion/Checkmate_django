from django.urls import path
from .views import LoginAPIView, RegisterAPIView

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='login'),
    path('register/', RegisterAPIView.as_view(), name='register'),
path('me/', UserInfoView.as_view(), name='user-info')
]