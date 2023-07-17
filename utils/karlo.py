import requests
import json

class karlo_agent:
    def __init__(self, config): 
        self.REST_API_KEY = config["tokens"]["karlo"]["key"]

    def t2i(self, prompt, negative_prompt):
        r = requests.post(
            'https://api.kakaobrain.com/v2/inference/karlo/t2i',
            json = {
                'prompt': prompt,
                'negative_prompt': negative_prompt,
                'nsfw_checker': True
            },
            headers = {
                'Authorization': f'KakaoAK {self.REST_API_KEY}',
                'Content-Type': 'application/json'
            }
        )
        # 응답 JSON 형식으로 변환
        response = json.loads(r.content)
        return response