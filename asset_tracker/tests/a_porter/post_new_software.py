import requests

rta = 'http://localhost:6544'
asset = 'http://localhost:6545'

token_url = rta + '/api/oauth-services/token/'
payload = {'grant_type': 'password', 'username': 'STHT1000', 'password': 'statioN1234'}
r = requests.post(token_url, params=payload)
print(r)

consultation_url = asset + '/api/update/?product=MedCapture'
headers = {'authorization': 'Bearer ' + r.json()['access_token']}
position = {'accuracy': 119, 'altitude': None, 'latitude': 48.844806399999996, 'longitude': 2.4333515}
json = {'version': '2.6.4-rc1', 'position': position}
r = requests.post(consultation_url, headers=headers, json=json)
print(r)
