import json
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(View):
    def post(self, request):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        username = body.get('username', '').strip()
        password = body.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is None:
            return JsonResponse({'error': 'Invalid credentials'}, status=401)

        login(request, user)
        return JsonResponse({'username': user.username, 'is_admin': user.is_staff})


@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(View):
    def post(self, request):
        logout(request)
        return JsonResponse({'status': 'logged out'})
