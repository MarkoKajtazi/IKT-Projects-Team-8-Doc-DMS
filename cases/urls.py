from django.urls import path

from . import views

urlpatterns = [
    path("my/", views.my_cases, name="my_cases"),
    path("queue/", views.work_queue, name="work_queue"),
    path("new/", views.new_submission, name="new_submission"),
    path("<int:pk>/", views.case_detail, name="case_detail"),
]