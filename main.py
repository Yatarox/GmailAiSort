import time
import requests
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
from transformers import pipeline
# Url de connexion à l'API Google
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Authentification Google
flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0)
service = build('gmail', 'v1', credentials=creds)

# Chargement initial de la liste des labels existants
listLabel = service.users().labels().list(userId='me').execute()


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


# Fonction pour créer un label s'il n'existe pas
def create_label(label_name):
    label_object = {
        'name': label_name,
        'labelListVisibility': 'labelShow',
        'messageListVisibility': 'show'
    }
    created_label = service.users().labels().create(userId='me', body=label_object).execute()
    print(f"Label {label_name} créé.")
    return created_label['id']
# Fonction pour attribuer un label à un email
def add_label(message_id, label_name):
    global listLabel  # Pour mettre à jour la liste globale si besoin
    existing_labels = {label['name']: label['id'] for label in listLabel['labels']}

    if label_name in existing_labels:
        label_id = existing_labels[label_name]  
    else:
        label_id = create_label(label_name)
        # Mise à jour de la liste des labels après création
        listLabel = service.users().labels().list(userId='me').execute()
        existing_labels = {label['name']: label['id'] for label in listLabel['labels']}

    body = {
        'addLabelIds': [label_id],
    }
    service.users().messages().modify(userId="me", id=message_id, body=body).execute()
    print(f"Label {label_name} ajouté à l'email {message_id}")


# Fonction pour demander au modèle local le label
def AskModelLabel(sender, subject, body):
    # Catégories possibles
    candidate_labels = [
        "Travail",
        "Personnel",
        "Urgent",
        "Promotion",
        "SpamMail",
        "Finance",
        "Support Technique",
        "Factures",
        "Voyages",
        "Réseaux Sociaux"
    ]
    # Texte complet de l'email
    email_content = f"Expéditeur: {sender}\nSujet: {subject}\nContenu: {body}"

    # Charger le modèle pré-entraîné localement
    classifier = pipeline("zero-shot-classification", model="valhalla/distilbart-mnli-12-1", device=0)



    # Faire la prédiction avec Hugging Face
    result = classifier(email_content, candidate_labels)

    # Retourner le label avec la plus haute probabilité
    label = result['labels'][0]  # Le label le plus probable
    print(f"L'IA a trouvé le label : {label}")
    return label


# Fonction pour calculer le temps restant
def time_remaining(timeFor100Mails, nbrEmailScrap):
    mailRestant = nbrEmailScrap
    mailRestant += 2
    tempsRestant = (mailRestant * timeFor100Mails) / 100
    if tempsRestant / 3600 > 1:
        tempsRestant /= 3600
        print(f"Temps restant {tempsRestant:.2f} H")
    elif tempsRestant / 60 > 1:
        tempsRestant /= 60
        print(f"Temps restant {tempsRestant:.2f} min")
    else:
        print(f"Temps restant {tempsRestant:.2f} sec")


# Fonction principale pour récupérer les emails et leur appliquer les labels
def recup_email(nbrEmailScrap):
    nbrMail = 0
    page_token = None
    while nbrMail < nbrEmailScrap:
        results = service.users().messages().list(userId='me', pageToken=page_token).execute()
        messages = results.get('messages', [])
        timeBefore100Mails = time.time()

        # Parcours des messages
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            headers = msg['payload']['headers']
            from_header = next(header['value'] for header in headers if header['name'] == 'From')
            subject_header = next(header['value'] for header in headers if header['name'] == 'Subject')
            content = get_email_content(msg)

            # On utilise l'IA locale pour classer l'email
            label = AskModelLabel(from_header, subject_header, content)
            add_label(message['id'], label)
            nbrMail += 1

            mettre_a_jour_interface(subject_header,nbrMail)
            print(f"Mail {nbrMail} sur {nbrEmailScrap} \n")

            if nbrMail >= nbrEmailScrap:
                break

        timeAfter100Mails = time.time()
        timeFor100Mails = timeAfter100Mails - timeBefore100Mails
        time_remaining(timeFor100Mails, nbrEmailScrap - nbrMail)

        print("Le programme est terminé")
        page_token = results.get('nextPageToken')
        if not page_token:
            break


import tkinter as tk
from tkinter import scrolledtext
import threading

# Interface graphique
def lancer_classement():
    try:
        nombre_mail = int(entry_nombre.get())
        log(f"Démarrage du classement pour {nombre_mail} mails...")


        # Créer un thread pour le traitement des emails
        threading.Thread(target=traiter_emails, args=(nombre_mail, service), daemon=True).start()

    except ValueError:
        log("Erreur : Entrez un nombre valide.")


def traiter_emails(nombre_mail, service):
    try:
        # Appel de recup_email avec la fonction de mise à jour de l'interface
        recup_email(nombre_mail)
    except Exception as e:
        log(f"Erreur pendant le traitement des emails : {e}")


def mettre_a_jour_interface(email_en_cours,nbrMail):
    label_email_courant.after(0, lambda: label_email_courant.config(text=f"En cours d'analyse : {email_en_cours}"))
    log(f"Le main numéro {str(nbrMail)} a été traité")


def log(message):
    text_area.after(0, lambda: text_area.insert(tk.END, message + "\n"))
    text_area.after(0, lambda: text_area.see(tk.END))


# Fenêtre principale
fenetre = tk.Tk()
fenetre.title("Classeur d'emails avec IA")
fenetre.geometry("600x400")

# Widgets
label_instruction = tk.Label(fenetre, text="Nombre de mails à classer :")
label_instruction.pack(pady=10)

entry_nombre = tk.Entry(fenetre, width=20)
entry_nombre.pack(pady=5)

bouton_lancer = tk.Button(fenetre, text="Lancer le classement", command=lancer_classement)
bouton_lancer.pack(pady=10)

text_area = scrolledtext.ScrolledText(fenetre, width=70, height=15)
text_area.pack(pady=10)

# Label pour afficher l'email en cours d'analyse
label_email_courant = tk.Label(fenetre, text="Aucun email en cours", font=("Arial", 10))
label_email_courant.pack(pady=5)

fenetre.mainloop()