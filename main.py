import requests

response = requests.get('https://www.amazon.com.br/PlayStation%C2%AE5-Digital-Pacote-ASTRO-Turismo/dp/B0F7Z9F9SD')


print(response.text)