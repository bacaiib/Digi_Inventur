from django import forms
from .models import artikel

class artikelForm(forms.Form):
    class Meta:
        model = artikel
        fields = ['CORTEXNR', 'HERST_NAME', 'HERST_ART_NR', 'ART_NAME', 'ANZAHL']