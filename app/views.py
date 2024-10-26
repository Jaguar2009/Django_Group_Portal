from django.shortcuts import render


def home(request):
    return render(request, 'portal_html/home.html')
