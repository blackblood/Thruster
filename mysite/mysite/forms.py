from django import forms


class BlogForm(forms.Form):
    title = forms.CharField(label="Title", max_length=100)
    body = forms.CharField(widget=forms.Textarea)

class UploadFileForm(forms.Form):
    title = forms.CharField(max_length=50)
    file = forms.FileField()