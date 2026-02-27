from django.urls import path

from .views import report_detail_view, translate_narrative_view, tts_narrative_view, upload_report_view

urlpatterns = [
    path("upload/", upload_report_view, name="report-upload"),
    path("translate/", translate_narrative_view, name="report-translate"),
    path("tts/", tts_narrative_view, name="report-tts"),
    path("<int:report_id>/", report_detail_view, name="report-detail"),
]
