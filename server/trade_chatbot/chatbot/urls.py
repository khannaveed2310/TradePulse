from django.urls import path
from .views import chat, check_status

urlpatterns = [
    path("chat/", chat),
    path("status/", check_status),
]