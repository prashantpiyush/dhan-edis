"""
Gmail related functions to read and delete emails.

On first run this will open a browser window to authenticate the app
and save the token in token.json file. On subsequent runs, it will
use the token from the file.

To correctly configure the Google app follow:
https://developers.google.com/gmail/api/quickstart/python
"""

import logging
import os
import re
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


def get_gmail_service():
    """
    The file token.json stores the user's access and refresh tokens, and is
    created automatically when the authorization flow completes for the first time.
    """
    scopes = ['https://mail.google.com/']
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', scopes)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', scopes)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail.py', 'v1', credentials=creds)
    return service


def delete_email():
    service = get_gmail_service()
    results = service.users().messages().list(
        userId='me',
        labelIds=['INBOX'],
        q="from:edis@cdslindia.co.in subject:Transaction OTP"
    ).execute()
    message = results.get('messages', [])[0]

    if not message:
        logger.warning('[delete_email] No messages from CDSL found to be deleted')
    else:
        logger.info("[delete_email] Found the message from CDSL, deleting it...")
        service.users().messages().delete(userId='me', id=message['id']).execute()
        logger.info("[delete_email] Successfully delete message from CDSL")


def get_otp_from_email(max_tries=5) -> str:
    service = get_gmail_service()
    try:
        results = service.users().messages().list(
            userId='me',
            maxResults=1,
            labelIds=['INBOX'],
            q="from:edis@cdslindia.co.in is:unread subject:Transaction OTP"
        ).execute()
        message = results.get('messages', [])[0]

        if not message:
            logger.warning('[get_otp] No messages from CDSL found.')
        else:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            email_headers = msg['payload']['headers']
            for values in email_headers:
                key = values["name"]
                if key == "From":
                    match_opt = re.search('(\d{6})', str(msg['snippet']))
                    return match_opt.group()

    except Exception as exp:
        logger.warning("[get_otp] Failed to read the email from CDSL", exp)

    if max_tries <= 0:
        logger.error("[get_otp] Failed to read email from edis. Giving up.")
        exit(1)

    # If email is not received, wait for 15 seconds and try again
    time.sleep(15)
    get_otp_from_email(max_tries=max_tries - 1)
