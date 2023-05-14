from __future__ import print_function

import base64
import datetime
import os.path
import re

import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://mail.google.com/']

data = pd.DataFrame(columns=['Textual', 'Numerical'])

def getSubject(msg):
	subject = ''
	for item in msg['payload']['headers']:
		if item['name'] == 'Subject':
			subject = item['value']
	return subject

def getSender(msg):
	sender = ''
	for item in msg['payload']['headers']:
		if item['name'] == 'From':
			sender = item['value']
	return sender

def getDate(msg):
    for header in msg['payload']['headers']:
        if header['name'] == 'Received':
            date_string = re.sub(r'by .+ with SMTP id .+;\s+', '', header['value'])
            date_string = re.sub(r'\s\([A-Z]+\)', '', date_string)
            pattern = r'\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), \d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} \d{2}:\d{2}:\d{2} [-+]\d{4}\b'
            match = re.search(pattern, date_string)
            if match:
                date_string = match.group(0)
            date_obj = datetime.datetime.strptime(date_string, '%a, %d %b %Y %H:%M:%S %z')
            timestamp = int(date_obj.timestamp())
            return timestamp
	
def getBody(msg):
	body = ''
	if 'parts' in msg['payload']:
		if 'data' in msg['payload']['parts'][0]['body']:
			body = base64.urlsafe_b64decode(msg['payload']['parts'][0]['body']['data']).decode('utf-8')
	return body

def createDataString(msg):
	return f'Subject: {getSubject(msg)} Body: {getBody(msg)} Sender: {getSender(msg)}'

def login():
	creds = None
	print('Checking credentials...')
	if os.path.exists('token.json'):
		creds = Credentials.from_authorized_user_file('token.json', SCOPES)
	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file(
				'credentials.json', SCOPES)
			creds = flow.run_local_server(port=0)
		with open('token.json', 'w') as token:
			token.write(creds.to_json())
	
	return creds

def main():
	creds = login()

	try:
		service = build('gmail', 'v1', credentials=creds)

		#save the first 20 unreads in the inbox to the dataframe
		results = service.users().messages().list(userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=20).execute()
		messages = results.get('messages', [])
		for message in messages:
			msg = service.users().messages().get(userId='me', id=message['id']).execute()
			data.loc[len(data)] = [createDataString(msg), getDate(msg)] # type: ignore
			print(f"Added {getSubject(msg)} to dataframe")
			data.to_parquet('val.parquet')

	except HttpError as err:
		print(err)

if __name__ == '__main__':
	main()