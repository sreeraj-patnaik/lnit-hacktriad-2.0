from django.urls import path

from .views import report_detail_view, upload_report_view

urlpatterns = [
    path("upload/", upload_report_view, name="report-upload"),
    path("<int:report_id>/", report_detail_view, name="report-detail"),
]
