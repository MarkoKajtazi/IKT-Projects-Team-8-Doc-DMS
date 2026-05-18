from django.urls import path

from . import views

urlpatterns = [
    path("my/", views.my_cases, name="my_cases"),
    path("queue/", views.work_queue, name="work_queue"),
    path("new/", views.new_submission, name="new_submission"),
    path("<int:pk>/", views.case_detail, name="case_detail"),
    path("<int:pk>/resubmit/", views.resubmit_case, name="resubmit_case"),
    path("<int:pk>/comment/", views.add_comment, name="add_comment"),
    path("<int:pk>/status/", views.change_status, name="change_status"),
    path("<int:pk>/assign/", views.assign_case, name="assign_case"),

]