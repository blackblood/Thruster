from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from .forms import BlogForm, UploadFileForm
from .models import Blog

def index(request):
    pass


def new(request):
    if request.method == "POST":
        form = BlogForm(request.POST)
        if form.is_valid():
            Blog.objects.create(request.POST)
            return HttpResponseRedirect("/create/")
    else:
        form = BlogForm()

    return render(request, "create.html", {"form": form})


def show(request):
    html = "<html><body><h1>This is the blog page</h1></body></html>"
    return HttpResponse(html)

def upload_document(request):
    if request.method == 'POST':
        print("request.POST: %s" % request.POST)
        print("request.FILES: %s" % request.FILES)
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            with open('name.txt', 'wb+') as destination:
                for chunk in request.FILES['file'].chunks():
                    destination.write(chunk)
            return HttpResponseRedirect('/success/url/')
    else:
        form = UploadFileForm()
    return render(request, 'upload.html', {'form': form})