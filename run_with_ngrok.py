import os
import time
from pyngrok import ngrok
from dotenv import load_dotenv

def run_ngrok():
    # .env 파일 로드
    load_dotenv()
    
    auth_token = os.getenv("NGROK_AUTH_TOKEN")
    if not auth_token:
        print("Error: NGROK_AUTH_TOKEN not found in .env file.")
        return

    # ngrok 인증 토큰 설정
    ngrok.set_auth_token(auth_token)

    try:
        # 포트 8000에 대해 HTTP 터널 생성
        print("Opening ngrok tunnel on port 8000...")
        public_url = ngrok.connect(8000).public_url
        print(f"\n" + "="*50)
        print(f"Ngrok Tunnel is Live!")
        print(f"Public URL: {public_url}")
        print(f"Admin Page: {public_url}/viewer.html")
        print("="*50 + "\n")
        
        print("Keep this script running to maintain the connection.")
        print("Press Ctrl+C to stop the tunnel.")
        
        # 스크립트가 즉시 종료되지 않도록 대기
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping ngrok tunnel...")
        ngrok.disconnect(public_url)
        print("Tunnel closed.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    run_ngrok()
