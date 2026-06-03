## 실행 방법

### 사전 요구사항
- Python 3.10+ / Node.js 18+

### 프로젝트 클론
```bash
git clone https://github.com/Cloud9-capstone-2026/cloud9.git
cd cloud9
```

### 환경 변수 (.env)
프론트엔드가 백엔드 API 주소를 찾도록 `frontend/.env` 파일을 만들고 아래 한 줄을 추가합니다.
```
REACT_APP_API_URL=http://localhost:8080
```
백엔드는 로컬에서 SQLite를 자동 사용하므로 별도 설정이 필요 없습니다.

### Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
python main.py
```
`http://localhost:8080` 에서 API가 동작하며, SQLite DB(`local.db`)가 자동 생성됩니다.

### Frontend (React)
```bash
cd frontend
npm install
npm start
```
`http://localhost:3000` 에서 화면이 열립니다.

### DB 초기화 (선택)
업로드된 거래·분석 데이터를 비웁니다.
```bash
cd backend
python reset_db.py
```
확인 메시지에 yes를 입력하면 실행됩니다.

### 사용 시나리오
1. (선택) DB 초기화 후 깨끗한 상태에서 시작합니다.
2. **업로드** — 매매내역 CSV 업로드 → 거래 분석
3. **대시보드** — 위험 점수 · 투자 성향 프로파일 확인
4. **리포트** — 등록된 매매 내역과 행동 분석 리포트를 확인

> **업로드 CSV 필수 컬럼** : `거래일자 · 종목명 · 거래구분 · 거래수량 · 거래단가 · 거래금액 · 수수료 · 거래세 · 정산금액`
> 샘플 데이터 : [`data/persona_a_clean.csv`](data/persona_a_clean.csv) (기존) → [`data/persona_b_clean.csv`](data/persona_b_clean.csv) (신규)

<br>

## 데모 (Live Demo)

**배포 주소 : https://canary-rust.vercel.app/**

설치 없이 배포된 버전에서 주요 기능을 확인할 수 있습니다.

- **업로드 & 분석** — 매매내역 CSV를 업로드할 시 이전에 없던 신규 거래 분석.
- **대시보드** — 위험 점수와 투자 성향 프로파일을 확인.
- **리포트** — 등록된 매매 내역과 행동 분석 리포트를 확인.
