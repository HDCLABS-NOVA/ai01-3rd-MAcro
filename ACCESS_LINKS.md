# 🎫 티켓 예매 시스템 접속 링크

## 📋 서버 정보
- **서버 상태**: Uvicorn 실행 중
- **포트**: 8000
- **주소**: 0.0.0.0:8000 (모든 네트워크 인터페이스)

---

## 🖥️ 로컬 접속 (현재 PC)

### 메인 페이지
- http://localhost:8000

### 주요 페이지
- **로그인**: http://localhost:8000/login.html
- **공연 선택**: http://localhost:8000/index.html
- **좌석 선택**: http://localhost:8000/seat_select.html
- **할인 선택**: http://localhost:8000/discount.html
- **예매자 정보**: http://localhost:8000/step3_booker.html
- **결제**: http://localhost:8000/step4_payment.html
- **완료**: http://localhost:8000/complete.html

### 관리/분석 페이지
- **로그 뷰어**: http://localhost:8000/viewer.html
- **공연창 로그**: http://localhost:8000/viewer_performance.html
- **예매창 로그**: http://localhost:8000/viewer_booking.html

---

## 🌐 네트워크 접속 (같은 Wi-Fi의 다른 기기)

### 메인 페이지
- http://192.168.14.199:8000

### 주요 페이지
- **로그인**: http://192.168.14.199:8000/login.html
- **공연 선택**: http://192.168.14.199:8000/index.html
- **좌석 선택**: http://192.168.14.199:8000/seat_select.html
- **할인 선택**: http://192.168.14.199:8000/discount.html
- **예매자 정보**: http://192.168.14.199:8000/step3_booker.html
- **결제**: http://192.168.14.199:8000/step4_payment.html
- **완료**: http://192.168.14.199:8000/complete.html

### 관리/분석 페이지
- **로그 뷰어**: http://192.168.14.199:8000/viewer.html
- **공연창 로그**: http://192.168.14.199:8000/viewer_performance.html
- **예매창 로그**: http://192.168.14.199:8000/viewer_booking.html

---

## 🔧 기타 네트워크 인터페이스

### WSL 접속
- http://172.17.96.1:8000

### 핫스팟 접속 (핫스팟 활성화 시)
- http://192.168.137.1:8000

---

## 📱 사용 가이드

### 1️⃣ 현재 PC에서 테스트
```
http://localhost:8000
```

### 2️⃣ 스마트폰/태블릿에서 테스트
1. 현재 PC와 **같은 Wi-Fi**에 연결
2. 다음 주소로 접속:
```
http://192.168.14.199:8000
```

### 3️⃣ 다른 컴퓨터에서 테스트
1. 같은 Wi-Fi 네트워크에 연결
2. 다음 주소로 접속:
```
http://192.168.14.199:8000
```

---

## 🎯 테스트 시나리오

### 일반 사용자 플로우
1. **로그인** → http://localhost:8000/login.html
2. **공연 선택** → http://localhost:8000/index.html
3. **대기열 통과** (자동)
4. **좌석 선택** → http://localhost:8000/seat_select.html
   - ⚠️ 35% 확률로 "이미 선택된 좌석입니다" 팝업
5. **할인 선택** → http://localhost:8000/discount.html
6. **예매자 정보 입력** → http://localhost:8000/step3_booker.html
7. **결제** → http://localhost:8000/step4_payment.html
8. **완료** → http://localhost:8000/complete.html

### 관리자/분석
- **로그 뷰어**: http://localhost:8000/viewer.html
  - 모든 사용자 행동 로그 확인
  - 마우스 궤적 시각화
  - 봇 탐지 분석

---

## 🔥 최신 업데이트

### 2026-01-31
- ✅ 좌석 선택 시 35% 확률로 "이미 선택된 좌석" 팝업 기능 추가
- ✅ 마우스 좌표 정규화 시스템 구현
  - 서로 다른 화면 해상도에서도 정확한 로그 시각화
  - viewport 크기 저장 및 정규화된 좌표 사용
- ✅ 로그 뷰어에서 해상도 무관 정확한 궤적 표시

---

## 💡 참고사항

- 서버는 `python main.py` 명령으로 실행됩니다
- 종료: `Ctrl + C`
- 로그 파일: `logs/` 디렉토리에 저장됨
- 브라우저 콘솔에서 추가 디버그 정보 확인 가능

---

Last Updated: 2026-01-31 09:31
