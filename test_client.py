import requests

# 서버 주소
server_url = 'http://localhost:5000'  # 예시로 localhost의 포트 5000 사용


def send_message(message):
    endpoint = f'{server_url}/chatbot'
    data = {'message': message}
    res = requests.post(endpoint, json=data)
    return res.json()


while True:
    user_message = input()

    response = send_message(user_message)
    print('\n' + response['message'])
