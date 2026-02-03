import uvicorn
from pyngrok import ngrok
from dotenv import load_dotenv
import os
import webbrowser
import time
import threading

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
        # 지역을 'jp'로 설정하여 속도 개선
        ngrok.set_auth_token(auth_token)
    
    # HTTP 터널 열기 (포트 8000)
    # pyngrok 최신 버전에서는 connect()에 region을 직접 넣으면 에러가 날 수 있으므로 기본 설정 사용하거나 config로 처리
    public_url = ngrok.connect(8000).public_url
    print(f"\n" + "="*50)
    print(f" * ngrok 서비스 주소: {public_url}")
    print(f" * 위 주소로 접속하세요!")
    print("="*50 + "\n")
    
    # 브라우저 자동 실행을 위한 함수
    def open_browser():
        time.sleep(2) # 서버 시작 대기
        print(f" * 브라우저를 엽니다: {public_url}")
        webbrowser.open(public_url)
    
    # 별도 스레드에서 브라우저 실행
    threading.Thread(target=open_browser, daemon=True).start()
    
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
