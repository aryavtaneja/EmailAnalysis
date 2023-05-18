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

data = pd.DataFrame(columns=['subject', 'sender', 'date', 'snippet', 'body', 'replied_to'])

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

def getSnippet(msg):
	snippet = msg['snippet']
	return snippet

def getRecipient(msg):
	recipient = ''
	for item in msg['payload']['headers']:
		if item['name'] == 'To':
			recipient = item['value']
	return recipient

def getBody(msg):
	body = ''
	#if payload is multipart, get the text/plain version of the body
	if 'parts' in msg['payload']:
		if 'data' in msg['payload']['parts'][0]['body']:
			body = base64.urlsafe_b64decode(msg['payload']['parts'][0]['body']['data']).decode('utf-8')
	#if payload is not multipart, get the text/plain version of the body
	else:
		if 'data' in msg['payload']['body']:
			body = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode('utf-8')

	return body

	return body

def getDate(msg):
	for header in msg['payload']['headers']:
		if header['name'] == 'Received':
			date_string = re.sub(r'by .+ with SMTP id .+;\s+', '', header['value'])
			date_string = re.sub(r'\s\([A-Z]+\)', '', date_string)
			pattern = r'\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), \d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} \d{2}:\d{2}:\d{2} [-+]\d{4}\b'
			match = re.search(pattern, date_string)
			if match:
				date_string = match.group(0)
			date = datetime.datetime.strptime(date_string, '%a, %d %b %Y %H:%M:%S %z')
			date = date.astimezone(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
			return date

def repliedTo(service, msg):
	#get the thread id of the message
	threadId = msg['threadId']

	#get all messages in the thread
	thread = service.users().threads().get(userId='me', id=threadId).execute()
	
	original_sender = getSender(msg)

	for message in thread['messages']:
		if getRecipient(message) == original_sender:
			return 1
		
	return 0

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

def save_first_five_hundred_messages(service, creds):
	results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=500).execute()
	messages = results.get('messages', [])

	msg_num = 0
	for message in messages:
		msg_num += 1
		msg = service.users().messages().get(userId='me', id=message['id']).execute()
		print(getDate(msg))
		#append data to dataframe
		replied_to = repliedTo(service, msg)
		data.loc[len(data)] = [getSubject(msg), getSender(msg), getDate(msg), getSnippet(msg), getBody(msg), replied_to] # type: ignore
		#save as parquet file
		data.to_parquet('data_unembedded.parquet')
		print(f'Saved row %d, with repliedTo value of %d' % (msg_num, replied_to))

	next_page_token = results.get('nextPageToken')

	return next_page_token


def save_five_hundred_messages(service, next_page_token, batch_num):
	results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=500, pageToken=next_page_token).execute()
	messages = results.get('messages', [])

	msg_num = batch_num * 500
	for message in messages:
		msg_num += 1
		msg = service.users().messages().get(userId='me', id=message['id']).execute()
		print(getDate(msg))	
		#append data to dataframe
		replied_to = repliedTo(service, msg)
		data.loc[len(data)] = [getSubject(msg), getSender(msg), getDate(msg), getSnippet(msg), getBody(msg), replied_to] # type: ignore
		#save as parquet file
		data.to_parquet('data_unembedded.parquet')
		print(f'Saved row %d, with repliedTo value of %d' % (msg_num, replied_to))

	next_page_token = results.get('nextPageToken')

	return next_page_token

def main():
	creds = login()

	try:
		service = build('gmail', 'v1', credentials=creds)
		
		print('Saving batch 1...')
		next_page_token = save_first_five_hundred_messages(service, creds)

		for x in range(500):
			print(f'Saving batch {x+2}...')
			next_page_token = save_five_hundred_messages(service, next_page_token, x+1)

	except HttpError as err:
		print(err)

if __name__ == '__main__':
	main()