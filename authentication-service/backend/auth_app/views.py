from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import JsonResponse

from .serializers import LoginSerializer


class LoginView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'message': 'Username and password are required',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        if username == 'user' and password == 'user123':
            return Response(
                {
                    'success': True,
                    'message': 'Login successful',
                    'username': username,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                'success': False,
                'message': 'Invalid username or password',
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    def health(request):
        return JsonResponse({'status': 'healthy'})