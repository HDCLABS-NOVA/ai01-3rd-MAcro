# API 명세서

| HTTP 메소드 | URL | 기능 |
| :--- | :--- | :--- |
| POST | /api/auth/signup | 회원가입 |
| POST | /api/auth/login | 로그인 |
| POST | /api/booking/start-token | 예매 시작 전 인증 토큰 발급 |
| POST | /api/queue/join | 대기열 진입 요청 |
| GET | /api/queue/status | 대기열 상태 및 순번 확인 |
| POST | /api/queue/enter | 대기열 통과 후 좌석 선택 권한 획득 |
| GET | /api/performances | 공연 목록 조회 |
| GET | /api/performances/{id} | 공연 상세 정보 조회 |
| POST | /api/logs | 로그 저장 (브라우저/행위) |
| GET | /api/logs | 로그 목록 조회 |
| GET | /api/logs/{file} | 특정 로그 상세 조회 |
| GET | /api/risk/runtime-status | AI 탐지 모델 및 임계값 상태 확인 |
| POST | /api/admin/performances | 공연 추가 |
| PUT | /api/admin/performances/{id} | 공연 수정 |
| DELETE | /api/admin/performances/{id} | 공연 삭제 |
| POST | /api/admin/restrict-user | 사용자 예매 제한 설정 |
| POST | /api/admin/unrestrict-user | 예매 제한 해제 |
| GET | /api/admin/restricted-users | 현재 제한 중인 사용자 목록 |
| GET | /api/admin/check-restriction/{email} | 특정 사용자 제한 여부 확인 |
| GET | /api/admin/restriction-history | 제재/해제 이력 조회 |
| GET | /api/admin/cancelled-bookings | 취소된 예매 내역 조회 |
| POST | /api/admin/cancel-booking | 예매 강제 취소 |
| GET | /api/mypage/bookings/{email} | 사용자의 예매 내역 조회 |
| POST | /api/mypage/update-delivery | 배송지 주소 수정 |
| GET | /api/reports | AI 분석 리포트 목록 조회 |
| GET | /api/reports/{filename} | 특정 AI 분석 리포트 상세 조회 |
