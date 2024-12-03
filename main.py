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
    # Récupérer la liste des labels existants de l'utilisateur
    labels = service.users().labels().list(userId='me').execute()
    
    # Rechercher l'ID du label par son nom
    label_id = None
    for label in labels.get('labels', []):
        if label['name'].lower() == label_name.lower():
            label_id = label['id']
            break
    
    # Si le label n'est pas trouvé, le créer
    if not label_id:
        print(f"Le label '{label_name}' n'a pas été trouvé. Création d'un nouveau label.")
        label_body = {
            'name': label_name,
            'labelListVisibility': 'labelShow',
            'messageListVisibility': 'show'
        }
        try:
            new_label = service.users().labels().create(userId='me', body=label_body).execute()
            label_id = new_label['id']
            print(f"Label '{label_name}' créé avec succès.")
        except Exception as error:
            print(f"Erreur lors de la création du label : {error}")
            return None
    
    # Ajouter le label au message
    body = {
        "addLabelIds": [label_id]
    }
    
    try:
        message = service.users().messages().modify(userId='me', id=message_id, body=body).execute()
        print(f"Label '{label_name}' ajouté au message {message_id}")
        return message
    except Exception as error:
        print(f"Erreur lors de l'ajout du label : {error}")
        return None


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
            label = AskLlamaLabel(from_header,subject_header,content)
            add_label(message['id'], label)
            nbrMail+=1
            print(nbrMail)
        time_remaining(timeBefore100Mails)


        # Passer à la page suivante
        page_token = results.get('nextPageToken')
        if not page_token:
            break
def AskLlamaLabel(sender,subject,body):
    question = f"Voici un e-mail avec l'émetteur : {sender}, le sujet : {subject}, et le contenu : {body}. Analyse-le et retourne uniquement l'une des 5 catégories suivantes : Travail, Personnel, Spame, Urgent, Promotion. Ne mets rien d'autre, aucune explication, juste le label."
    data = {
        "model": "mistral",
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
