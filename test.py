import requests

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

AskLlamaLabel("galleyhugo@gmail.com","reunion Venredi","Je vous invite a la reunion de vendredi concernant le mmeting avec Patrick Cordialement ")