import time
import sqlite3
import requests

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Authentification
flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0)
service = build('gmail', 'v1', credentials=creds)

conn = sqlite3.connect('emails.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS emails (
    id TEXT PRIMARY KEY,
    thread_id TEXT,
    label TEXT
);
''')
conn.commit()
# Fonction pour récupérer le contenu du message
def get_email_content(msg):
    body = None
    if 'data' in msg['payload']['body']:
        body = msg['payload']['body']['data']
    elif 'parts' in msg['payload']:
        for part in msg['payload']['parts']:
            if part['mimeType'] == 'text/plain':  # Texte brut
                body = part['body']['data']
                break
            elif part['mimeType'] == 'text/html':  # HTML
                body = part['body']['data']
                break

    if body:
        return base64.urlsafe_b64decode(body).decode('utf-8')
    else:
        return "Aucun contenu disponible"
def recup_email(nbrEmailScrap):

    def time_remaining():
        mailRestant = nbrEmailScrap
        mailRestant -=100
        tempsRestant = ((mailRestant * timeFor100Mails) / 100) / 3600
        if tempsRestant > 1:
            print(f"Temps restant {tempsRestant} H")
        elif tempsRestant / 60 > 1:
            tempsRestant /= 60
            print(f"Temps restant {tempsRestant} min")
        else:
            print(f"Temps restant {tempsRestant} sec")



    nbrMail = 0
    # Récupérer les messages avec pagination
    page_token = None
    while nbrMail <= nbrEmailScrap:
        # Récupérer la liste des messages
        results = service.users().messages().list(userId='me', pageToken=page_token).execute()
        messages = results.get('messages', [])
        timeBefore100Mails = time.time()
        # Parcourir les messages
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            headers = msg['payload']['headers']
            from_header = next(header['value'] for header in headers if header['name'] == 'From')
            subject_header = next(header['value'] for header in headers if header['name'] == 'Subject')
            content = get_email_content(msg)
            label = AskLlamaLabel(from_header,subject_header,content)
            nbrMail+=1
            cursor.execute('''
                    INSERT OR IGNORE INTO emails (id, thread_id,label)
                    VALUES (?, ?, ?)
                    ''', (msg['id'], msg['threadId'],label))
            conn.commit()
            print(nbrMail)
        time_remaining()


        # Passer à la page suivante
        page_token = results.get('nextPageToken')
        if not page_token:
            break
def AskLlamaLabel(sender,subject,body):
    question = f"Je vais te donner un mail avec le nom de l'emmeteur le sujet et le contenu tu devra me redonner uniquement et seulement 1 mot pour categotiser se mail pour pouvoir le lableliser : voici l'emeteur : {sender} avec le sujet : {subject} et le corps du mail : {body}, retourne mot seulkement le lable sans rien de plus"

    # Préparation des données à envoyer
    data = {
        "model": "llama3.1",
        "messages": [{'role': 'user', "content": question}],
        'stream': False
    }
    url = "http://localhost:11434/api/chat"

    try:
        # Envoi de la requête POST
        response = requests.post(url, json=data)
        response.raise_for_status()
        response_json = response.json()

        # Récupération de la réponse de Llama
        ai_reply = response_json.get("message", {}).get("content", "No reply received.")
        print(ai_reply)
        return ai_reply
    except requests.exceptions.RequestException as e:
        print("Une erreur a eu lieu:", e)
    except KeyError:
        print("Erreur de saisie:", response.text)

recup_email(94600)
