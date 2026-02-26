from django import forms

from .models import MedicalReport


class MedicalReportUploadForm(forms.ModelForm):
    ocr_text = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 8,
                "placeholder": (
                    "Optional: Paste report text or simple lines like\n"
                    "Hemoglobin 11.2 g/dL 12-16\n"
                    "WBC 7000 cells/uL 4000-11000"
                ),
            }
        ),
        label="Report Text (optional)",
    )

    class Meta:
        model = MedicalReport
        fields = ("report_file", "report_date", "ocr_text")
        widgets = {
            "report_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["report_file"].required = False

    def clean(self):
        cleaned_data = super().clean()
        report_file = cleaned_data.get("report_file")
        ocr_text = (cleaned_data.get("ocr_text") or "").strip()
        if not report_file and not ocr_text:
            raise forms.ValidationError("Upload a file or paste report text.")
        return cleaned_data
