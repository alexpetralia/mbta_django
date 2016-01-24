from django.shortcuts import render
from django.http import HttpResponse

def about(request):
    return render(request, 'about.jinja', {})

def load_testing(request):
	key = 'loaderio-53771fef83b8cfc0ca6f002a28425d3f'
	return HttpResponse(key)