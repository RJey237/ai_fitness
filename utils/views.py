from rest_framework import viewsets
from django.http import JsonResponse
from .firebase import send_fcm_v1_notification
from twilio.rest import Client
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from rest_framework.decorators import action

def test_push(request):
    device_token = 'YOUR_DEVICE_TOKEN'
    title = 'Tired!'
    body = 'I am tired of tireness!'

    status_code, response = send_fcm_v1_notification(device_token, title, body)
    return JsonResponse({'status': status_code, 'response': response})




class SendSMSViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['post'])
    def send_sms(self, request):
        phone_number = request.data.get('phone_number')
        if not phone_number:
            return Response({'error': 'Phone number is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            account_sid = ''
            auth_token = ''
            client = Client(account_sid, auth_token)

            verification_check = client.verify \
                .v2 \
                .services('') \
                .verifications \
                .create(to=phone_number, channel='sms')
            return Response({'message': verification_check.status}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def verify_sms(self, request):
        phone_number = request.data.get('phone_number')
        code = request.data.get('code')
        if not phone_number or not code:
            return Response({'error': 'Phone number and code are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            account_sid = ''
            auth_token = ''
            client = Client(account_sid, auth_token)

            verification_check = client.verify \
                .v2 \
                .services('') \
                .verification_checks \
                .create(to=phone_number, code=code)
            
            if verification_check.status == 'approved':
                return Response({'message': 'Verification successful!'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Verification failed!'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)