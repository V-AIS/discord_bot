"""Gemini Gateway 호출 헬퍼.

커맨드(cogs/llms.py)와 아카이빙(bot.py) 양쪽에서 쓰므로 한 곳에 둔다.
게이트웨이 주소는 config.json 의 TOKENS.GOOGLE.HOST 에서만 읽는다.
내부 주소를 코드 기본값으로 두면 공개 저장소에 그대로 남는다.
"""

import aiohttp

MODEL = "gemini-3.5-flash-lite"
REQUEST_TIMEOUT_SECONDS = 60


def gateway_from(config: dict) -> str:
    """config 에서 게이트웨이 주소를 꺼낸다. 없으면 빈 문자열."""
    host = config.get("TOKENS", {}).get("GOOGLE", {}).get("HOST") or ""
    return host.rstrip("/")


async def generate(gateway: str, prompt: str, max_output_tokens: int = 1024) -> str:
    """게이트웨이에 질의하고 답변 텍스트를 돌려준다.

    :raises RuntimeError: 응답에 본문이 없을 때 (안전 필터 차단·토큰 초과 등)
    :raises aiohttp.ClientError: 통신 실패 또는 4xx/5xx
    """
    url = f"{gateway}/v1beta/models/{MODEL}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": max_output_tokens,
        },
    }

    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json=payload) as response:
            # 4xx/5xx 본문도 JSON 이라 status 를 먼저 확인하지 않으면
            # 아래 키 접근이 엉뚱한 KeyError 로 바뀐다.
            response.raise_for_status()
            data = await response.json()

    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"candidates 없음: {str(data)[:300]}")

    candidate = candidates[0]
    parts = (candidate.get("content") or {}).get("parts") or []
    text = "".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise RuntimeError(
            f"본문이 비어 있음 (finishReason={candidate.get('finishReason')})"
        )
    return text
