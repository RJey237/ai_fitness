import json
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

# Path to your Firebase service account key
SERVICE_ACCOUNT_FILE = 'key.json'

# Your Firebase project ID
PROJECT_ID = 'fitnessio-a553c'

def get_access_token():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/firebase.messaging']
    )
    request = Request()
    credentials.refresh(request)
    return credentials.token

def send_fcm_v1_notification(device_token, title, body, data_payload=None):
    access_token = get_access_token()
    url = f"https://fcm.googleapis.com/v1/projects/{PROJECT_ID}/messages:send"

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json; UTF-8',
    }

    message = {
        "message": {
            "token": device_token,
            "notification": {
                "title": title,
                "body": body
            },
            "android": {
                "priority": "high"
            }
        }
    }

    if data_payload:
        message["message"]["data"] = data_payload

    response = requests.post(url, headers=headers, json=message)
    return response.status_code, response.json()
