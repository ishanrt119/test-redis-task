from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def home(request):
    return Response({'message': 'Hello this is home page'})


@api_view(['GET'])
def contact(request):
    return Response({'message': 'Hello this is contact page'})
