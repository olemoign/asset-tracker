import requests

rta = 'http://localhost:6544'
asset = 'http://localhost:6545'

token_url = rta + '/api/oauth-services/token/'
payload = {'grant_type': 'password', 'username': 'STHT1000', 'password': 'statioN1234'}
r = requests.post(token_url, params=payload)
print(r)

consultation_url = asset + '/api/update/?product=MedCapture'
headers = {'authorization': 'Bearer ' + r.json()['access_token']}

with open('files/test_post_new_software.json', 'rb') as j_son:
    r = requests.post(consultation_url, headers=headers, files={'json': j_son})
    print(r)
