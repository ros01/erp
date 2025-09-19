from .models import *

class FormProcessingForm(forms.ModelForm):
    class Meta:
        model = FormProcessing
        fields = ["application_url", "visa_username", "visa_password", "pdf_copy"]



