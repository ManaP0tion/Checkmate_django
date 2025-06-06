# ble/urls.py
from django.urls import path
from .views import mock_advertise, mock_stop_session

urlpatterns = [
    path("advertise/", mock_advertise, name="mock_advertise"),
    path("stop-session/", mock_stop_session, name="mock_stop_session"),
]