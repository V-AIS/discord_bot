import requests
import json

class kakao_agent:
    def __init__(self, config): 
        self.REST_API_KEY = config["TOKENS"]["KAKAO"]["KEY"]

    def karlo_t2i(self, prompt, negative_prompt):
        r = requests.post(
            'https://api.kakaobrain.com/v2/inference/karlo/t2i',
            json = {
                "version": "v2.1", 
                'prompt': prompt,
                'negative_prompt': negative_prompt,
                'guidance_scale': 10.0,
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
    
    def kogpt_req(self, prompt, max_tokens = 1, temperature = 1.0, top_p = 1.0, n = 1):
        r = requests.post(
        'https://api.kakaobrain.com/v1/inference/kogpt/generation',
        json = {
            'prompt': prompt,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'top_p': top_p,
            'n': n
        },
        headers = {
            'Authorization': 'KakaoAK ' + self.REST_API_KEY,
            'Content-Type': 'application/json'
            }
        )
        # 응답 JSON 형식으로 변환
        response = json.loads(r.content)
        return response