import json
import pandas as pd
import requests
import sys
import time

#from plotnine import ggplot, aes, geom_bar, theme_minimal, scale_fill_manual, labs


def download_sentiment(data, api_key):
    sentiments = {}
    responses = []
    max_chars = 1000

    try:
        for item in data:
            text = item['cuerpo_articulo']
            text = text.replace('\n', ' ')
            if len(text) > max_chars:
                text = text[:max_chars]

            url = 'https://api.api-ninjas.com/v1/sentiment'

            payload = {
                'text': text  # parametros que le pasamos a la API, en este caso solo tenemos text
            }

            headers = {
                'X-Api-Key': api_key  # esto esta en la API-Ninjas
            }

            r = requests.get(url, params=payload, headers=headers)
            response = r.json()

            if r.status_code == requests.codes.ok:
                score = response["sentiment"]
                print('Text: %s' % (text))
                print('This document is: %s' % (score))

                if (score in sentiments):
                    sentiments[score] = sentiments[score] + 1
                else:
                    sentiments[score] = 1
            else:
                print("Error:", response.status_code, response.text)

            time.sleep(1)

            responses.append(response)
        return responses, sentiments
    except ValueError:
        e = sys.exc_info()[0]
        print('\nException: ' + str(e))


api_key = 'TYNyCwcyMmBRGpAAJHARKg==0ep3GLQ2GX9ozNKh'

with open('data/vogue_celebrities_data.json', encoding='utf-8') as file:
    data = json.load(file)

responses, sentiments = download_sentiment(data=data, api_key=api_key)

with open('data/vogue_celebrities_sentiment.json', 'w', encoding='utf-8') as file:
    json.dump(responses, file, ensure_ascii=False, indent=4)


