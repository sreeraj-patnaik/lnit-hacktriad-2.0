from django.urls import path
from .views import SimplifyReportView

urlpatterns = [
    path("simplify-report/", SimplifyReportView.as_view(), name="simplify-report"),
]
