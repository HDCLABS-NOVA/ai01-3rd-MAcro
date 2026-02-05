import uvicorn
from pyngrok import ngrok
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

def start_ngrok():
    # 기존 터널 모두 종료 (중복 세션 방지)
    try:
        tunnels = ngrok.get_tunnels()
        for tunnel in tunnels:
            ngrok.disconnect(tunnel.public_url)
    except:
        pass

    # ngrok authtoken 및 지역(region) 설정
    auth_token = os.getenv("NGROK_AUTHTOKEN")
    if auth_token:
        ngrok.set_auth_token(auth_token)
    
    # 고정 도메인 설정 확인
    ngrok_domain = os.getenv("NGROK_DOMAIN")
    
    # HTTP 터널 열기 (포트 8000)
    if ngrok_domain:
        public_url = ngrok.connect(8000, domain=ngrok_domain).public_url
    else:
        public_url = ngrok.connect(8000).public_url
    print(f"\n" + "="*50)
    print(f" * ngrok 서비스 주소: {public_url}")
    print(f" * 위 주소로 접속하세요!")
    print("="*50 + "\n")
    return public_url

if __name__ == "__main__":
    try:
        start_ngrok()
        print(" * FastAPI 서버를 시작합니다...")
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    except KeyboardInterrupt:
        print("\n * 서버를 종료합니다...")
        ngrok.kill()
    except Exception as e:
        print(f"\n * 오류 발생: {e}")
        ngrok.kill()
