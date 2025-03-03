# tradehive

## 개요

이번 프로젝트는 Django를 최대한 활용하여 복잡하고 빠른 성능을 추구하는 코인거래소를 만들기 위해 진행되었습니다.

## 프로젝트 진행 과정

### 1일차

- ChatGPT를 사용해 프로젝트에 필요한 정보 설정
    - 프로젝트 이름
    - 프로젝트에 들어갈 기능
        1. 사용자 관리
        2. 거래 시스템
        3. 지갑 및 자산 관리
        4. 보안 기능
        5. 성능 및 안정성 강화
        6. 법적 준수
        7. 관리자 도구
        8. 기타 부가 기능
- Django를 사용해 사용자 관리 기능 중 회원가입과 로그인 서비스를 제작
    1. 사용자 모델 확장
    2. 회원가입과 로그인 기능 추가 및 테스트 코드 작성
    3. HTTPS 사용
    4. 쿠키 만료 시간 설정
    5. 사용자 비활성화 시 자동 로그아웃

### 2일차

- API 서버로 변경
    - HTML 페이지를 사용하는 세션 기반에서 JWT를 사용하는 API 기반으로 변경
- JWT에 보안 추가
    - 암호화 키, 토큰 생명주기 및 암호화 알고리즘, 헤더 타입 등 설정
    - 블랙리스트 활성화
        - 로그아웃 시 자동으로 블랙리스트가 되도록 로직 추가

### 3일차

- MFA 지원
    - QR 코드를 사용하여 Django에서 MFA를 사용할 수 있도록 추가
- serializer와 View의 역할 분리
    - serializer: 검증 및 데이터 가공
    - View: request와 response 전달

### 4일차

- 개인 정보 수정 기능 추가
    - GET으로 사용자 프로필 정보 가져오기
    - PATCH로 사용자 프로필 정보 수정하기

### 5일차

- 개인 정보 수정 기능 중 DELETE 추가
- 비밀번호 변경 기능 추가
- View와 Test 중 코드의 중복이 존재해 내용을 축약할 수 있는 코드가 존재하는 경우 이를 축약

### 6일차

- 거래 시스템 기능 추가
    - 시장가/지정가 주문 기능 추가
    - 실시간 주문 매칭 엔진 설정: Redis
- 원활한 서비스 및 테스트를 위한 container 사용: docker

### 7일차

- 다양한 거래 페어 지원을 위한 기능 추가
    - 거래 페어 데이터에 대한 CRUD 추가

### 8일차

- View에 대한 권한 검토 및 테스트 변경
- Github Action을 사용한 CI/CD 설정
    - 테스트 자동화 설정

### 9일차

- 거래소에서 지원하는 자산들에 대한 리스트 관리 기능 추가
    - 기존 로직에서 사용하던 자산 데이터를 연결 및 테스트

### 10일차

- nginx를 사용한 로드 밸런싱 추가

### 11일차

- gunicorn을 사용한 멀티 스레딩 추가

### 12일차

- 실시간 차트 기능 추가
- 실시간 체결 데이터 반영
    - WebSocket으로 실행

### 13일차

- application에 따른 기능 정리
    - order의 시장 관련 로직 markets로 이동
- 기술적 분석 도구 기능 추가
- docker container 갯수 조정
    - web container 갯수 조정
    - image 생성 과정 변경

### 14일차

- 사용자 가상자산 지갑 기능 추가
    - 지갑 입출금 기능 추가
    - 주문 시 자산 확인 과정 추가
- 빠른 개발을 위한 개발환경 container 구성

### 15일차

- 거래소 보호 기능 추가
    - 방화벽 추가
    - Postgresql의 SSH 사용

### 16일차

- 방화벽 기능 고도화
    - 각 서비스 별 동일 CA 기반 crt/key로 분리
- action 메모리 부족 해결
    - 테스트 grouping을 사용한 parallelization 적용
    - self-hosted runner 사용
    - action이 종료된 후 남는 container 등을 정리하기 위한 단계 추가

### 17일차

- DDoS 방어 로직 구축
    - nginx에 관련 설정 추가
    - django에 middleware 추가 및 기록과 추적을 위한 DB 구성
