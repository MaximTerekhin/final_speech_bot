import requests
from config import MAX_GPT_TOKENS_FOR_QUERE, SYSTEM_CONTENT, FOLDER_ID


res = requests.get(url="http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token",
                   headers={
                      "Metadata-Flavor": "Google"})
IAM_TOKEN = res.json()['access_token']


def speech_to_text(data):
    params = "&".join([
        "topic=general",
        f"folderId={FOLDER_ID}",
        "lang=ru-RU"
    ])
    headers = {
        'Authorization': f'Bearer {IAM_TOKEN}',
    }
    response = requests.post(
        f"https://stt.api.cloud.yandex.net/speech/v1/stt:recognize?{params}",
        headers=headers,
        data=data
    )
    decoded_data = response.json()
    if decoded_data.get('error_code') is None:
        return True, decoded_data.get('result'), int(len(decoded_data.get('result')))
    else:
        return False, 'При запросе произошла ошибка, попробуйте снова.'

def text_to_speech(text, voice, emotion):
    headers = {
        'Authorization': f'Bearer {IAM_TOKEN}',
    }
    data = {
        'text': text,
        'lang': 'ru-RU',
        'voice': voice,
        'emotion': emotion,
        'speed': 1,
        'format': 'mp3',
        'folderId': FOLDER_ID
    }
    response = requests.post('https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize', headers=headers, data=data)
    if response.status_code == 200:
        with open('my_voice.ogg', 'wb') as my_file:
            result = response.content
            my_file.write(result)
            return result
    else:
        print(f'Ошибка {response.status_code}')





# def count_gpt_tokens(text):
#     url = "https://llm.api.cloud.yandex.net/foundationModels/v1/tokenizeCompletion"
#     headers = {
#         'Authorization': f'Bearer {IAM_TOKEN}',
#         'Content-Type': 'application/json'
#     }
#     data = {
#         'modelUri': f"gpt://{FOLDER_ID}/yandexgpt-lite",
#         'max_tokens': MAX_GPT_TOKENS,
#         'messages': [{
#             'role': 'user', 'text': text
#         },
#             {'role': 'system', 'text': SYSTEM_CONTENT}]
#     }


    # print(data)
    # tokens = requests.post(url=url, json=data, headers=headers).json()['tokens']
    # print(len(tokens))
    # return len(tokens)

# def count_gpt_tokens(messages):
#     url = "https://llm.api.cloud.yandex.net/foundationModels/v1/tokenizeCompletion"
#     data = {
#         "modelUri": f"gpt://{FOLDER_ID}/yandexgpt/latest",
#         "maxTokens": MAX_GPT_TOKENS,
#         "messages": []
#     }
#     headers = {
#         'Authorization': f'Bearer {IAM_TOKEN}',
#         'Content-Type': 'application/json'}
#
#     for ell in messages:
#         data['messages'].append(ell)
#
#
#     print(data)
#     print()
#
#
#     count_tokens = requests.post(
#         url=url,
#         json=data,
#         headers=headers
#     )
#     print(count_tokens.json())
#     tokens = count_tokens.json()['tokens']
#     print(count_tokens.json()['tokens'])
def count_gpt_tokens(messages):
    headers = {
        'Authorization': f'Bearer {IAM_TOKEN}',
        'Content-Type': 'application/json'
    }

    data = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt/latest",
        'maxTokens': MAX_GPT_TOKENS_FOR_QUERE,
        'messages': [{'role': 'system', 'text': SYSTEM_CONTENT},
                     {'role': 'user', 'text': messages}]
    }



    result = requests.post(
        "https://llm.api.cloud.yandex.net/foundationModels/v1/tokenizeCompletion",
        json=data,
        headers=headers
    )
    count_tokens = result.json()['tokens']
    print(data)
    print()
    print(count_tokens)

    return len(count_tokens)










def ask_gpt(text):
    print(text)
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        'Authorization': f'Bearer {IAM_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        'modelUri': f"gpt://{FOLDER_ID}/yandexgpt-lite/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 1,
            "maxTokens": MAX_GPT_TOKENS_FOR_QUERE,
        },
        'messages': [{'role': 'system','text': SYSTEM_CONTENT},
                    {'role': 'user','text': text}]
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            return False, f"Ошибка GPT. Статус-код: {response.status_code},"
        answer = response.json()['result']['alternatives'][0]['message']['text']
        return True, answer
    except:
         return False, "Ошибка при обращении к GPT", 0