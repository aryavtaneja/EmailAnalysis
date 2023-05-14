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

data = pd.DataFrame(columns=['Subject', 'Sender', 'Body', 'Snippet', 'Replied To'])

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

def getRecipient(msg):
	recipient = ''
	for item in msg['payload']['headers']:
		if item['name'] == 'To':
			recipient = item['value']
	return recipient


def getSnippet(msg):
	return msg['snippet']

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
	results = service.users().messages().list(userId='me', labelIds=['INBOX', 'IMPORTANT'], maxResults=500).execute()
	messages = results.get('messages', [])

	msg_num = 0
	for message in messages:
		msg_num += 1
		msg = service.users().messages().get(userId='me', id=message['id']).execute()
		#append data to dataframe
		data.loc[len(data)] = [getSubject(msg), getSender(msg), getDate(msg), getLabels(msg), getBody(msg), repliedTo(service, msg)] # type: ignore
		#save as parquet file
		data.to_parquet('data2.parquet')
		print(f'Saved row %d, with repliedTo value of %d' % (msg_num, repliedTo(service, msg)))

	next_page_token = results.get('nextPageToken')

	return next_page_token


def save_five_hundred_messages(service, next_page_token, batch_num):
	results = service.users().messages().list(userId='me', labelIds=['INBOX', 'IMPORTANT'], maxResults=500, pageToken=next_page_token).execute()
	messages = results.get('messages', [])

	msg_num = batch_num * 500
	for message in messages:
		msg_num += 1
		msg = service.users().messages().get(userId='me', id=message['id']).execute()
		print(getDate(msg))	
		#append data to dataframe
		data.loc[len(data)] = [getSubject(msg), getSender(msg), getDate(msg), getLabels(msg), getBody(msg), repliedTo(service, msg)] # type: ignore
		#save as parquet file
		data.to_parquet('data2.parquet')
		print(f'Saved row %d, with repliedTo value of %d' % (msg_num, repliedTo(service, msg)))

	next_page_token = results.get('nextPageToken')

	return next_page_token

def main():
	creds = login()

	try:
		service = build('gmail', 'v1', credentials=creds)
		
		print('Saving batch 1...')
		next_page_token = save_first_five_hundred_messages(service, creds)

		for x in range(200):
			print(f'Saving batch {x+2}...')
			next_page_token = save_five_hundred_messages(service, next_page_token, x+1)

	except HttpError as err:
		print(err)

if __name__ == '__main__':
	main()