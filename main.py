import time
import requests

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Authentification
flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0)
service = build('gmail', 'v1', credentials=creds)

data = service.users().labels().list(userId='me').execute()

# Fonction pour récupérer le contenu du message
def get_email_content(msg):
    body = None
    if 'data' in msg['payload']['body']:
        body = msg['payload']['body']['data']
    elif 'parts' in msg['payload']:
        for part in msg['payload']['parts']:
            if part['mimeType'] == 'text/plain':  
                body = part['body']['data']
                break
            elif part['mimeType'] == 'text/html':  
                body = part['body']['data']
                break

    if body:
        return base64.urlsafe_b64decode(body).decode('utf-8')
    else:
        return "Aucun contenu disponible"
def add_label(message_id, label_name):
    for label in data['labels']:
        if label['name'] in label_name or label_name in label['name']:
            body = {
                'addLabelIds': label['id'],
            }
            service.users().messages().modify(userId="me",id=message_id, body=body).execute()
            print(f"Label {label['name']} ajouté à l'email {message_id}")
            return
    print("Aucun Label trouvé on skip")


def recup_email(nbrEmailScrap):

    def time_remaining(timeFor100Mails):
        mailRestant = nbrEmailScrap
        mailRestant -= 100
        tempsRestant = ((mailRestant * timeFor100Mails) / 100) / 3600
        if tempsRestant > 1:
            print(f"Temps restant {tempsRestant} H")
        elif tempsRestant / 60 > 1:
            tempsRestant /= 60
            print(f"Temps restant {tempsRestant} min")
        else:
            print(f"Temps restant {tempsRestant} sec")


    nbrMail = 0
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
            label = AskModelLabel(from_header,subject_header,content,"mistral-small")
            add_label(message['id'], label)
            nbrMail+=1
            print(f"Mail {nbrMail} sur {nbrEmailScrap} \n")
        time_remaining(timeBefore100Mails)


        # Passer à la page suivante
        page_token = results.get('nextPageToken')
        if not page_token:
            break
def AskModelLabel(sender,subject,body,modelName):
    question = f"Voici un e-mail avec l'émetteur : {sender}, le sujet : {subject}, et le contenu : {body}. Analyse-le et retourne uniquement l'une des 5 catégories suivantes : Travail, Personnel, SpamMail, Urgent, Promotion. Ne mets rien d'autre, aucune explication, juste le label."
    data = {
        "model": modelName,
        "messages": [{'role': 'user', "content": question}],
        'stream': False
    }
    url = "http://localhost:11434/api/chat"

    try:
        # Envoi de la requête POST
        response = requests.post(url, json=data)
        response.raise_for_status()
        response_json = response.json()

        # Récupération de la réponse du Modele
        ai_reply = response_json["message"]["content"]
        print(f"L'IA a trouvé le label : {ai_reply}")
        return ai_reply
    except requests.exceptions.RequestException as e:
        print("Une erreur a eu lieu:", e)

recup_email(100)
