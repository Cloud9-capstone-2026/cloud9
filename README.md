<p align="left">
  <img src="./frontend/src/logo3.png" alt="Canary Logo" width="800"/>
</p>

### 반복적인 손실을 겪는 개인 주식 투자자를 위한 AI 기반 매매 행동 분석 및 맞춤형 투자 습관 개선 플랫폼

> **"시장을 분석하는 것이 아니라, 나 자신을 분석한다."**

<br>

## 프로젝트 소개
 
Canary는 개인 주식 투자자의 매매 로그를 AI로 분석하여 비이성적 행동 패턴을 자동으로 탐지하고, 손실의 원인을 데이터 기반으로 설명하는 매매 행동 분석 및 맞춤형 투자 습관 점검 플랫폼입니다.
 
투자자의 실패 원인을 '정보 부족'이 아닌 '행동 통제 실패'에서 찾고, 객관적인 데이터 분석을 통해 투자자 스스로 자신의 매매 패턴을 인지할 수 있도록 도움으로써 실질적인 손실 방어와 건강한 투자 습관 형성을 지원합니다.

<br>

## 프로젝트 배경 및 문제 정의

### 왜 대다수의 개인 투자자는 시장에서 패배하는가?

* **정보의 문제가 아닌 행동의 문제:** 국내 개인 투자자 수가 역대 최고치를 기록하고 있으나, 대다수가 명확한 기준 없이 FOMO, 패닉셀 등 비이성적 심리에 기반한 매매로 손실을 반복합니다.
  
* **기존 서비스의 한계:** 대부분의 플랫폼은 무엇을 살 것인가(**What to buy**)에만 집중할 뿐, 정작 투자 실패의 핵심인 나는 왜 잃는가(**Why I lose**)에 대한 답을 주지 못합니다.

### Canary의 해결책
Canary는 수익 창출이 아닌, 손실을 유발하는 행동을 줄이는 데 집중합니다. 사용자의 매매 데이터 분석을 통해 무의식중에 반복되는 비이성적 패턴을 객관적으로 식별하여 손실 원인을 스스로 인지하고 투자 패턴을 개선할 수 있도록 지원합니다. 장기적으로 사용자의 실질적인 손실 방어 및 건전한 투자 습관 형성을 유도합니다.

<br>

## 주요 기능 (Key Features)

> 아래 기능은 목표 제품 기준이며, 현재 MVP는 Rule·Statistical 2계층 탐지까지 구현되어 있습니다 (LSTM·XAI·자가진단은 설계/개발 중).

### 1. 투자 성향 진단
사용자의 매매 데이터를 기반으로 행동재무학 관점의 투자자 페르소나를 도출합니다.
  
* **Phase1 (자가진단):** 회원가입 시 사용자가 각 성향 항목을 낮음 / 중간 / 높음으로 직접 평가합니다. 과거 매매 기록이 존재하지 않는 신규 사용자의 경우, 자가진단 결과를 성향 프로파일의 초기 기준값으로 사용합니다.


| 성향 항목 | 설명 | 측정 피처 |
| --- | --- | --- |
| 장기보유 성향 | 포지션을 오래 유지하는 경향 | 평균 보유 기간, 중도 청산 비율 |
| 손절회피 성향 | 손실 포지션을 끊지 못하는 경향 | PLR, 손실 포지션 평균 보유일 |
| 손실 직후 재진입 성향 | 손실 청산 직후 재진입하는 경향 | 손실 청산 후 15분/1시간 내 재진입률 |
| FOMO(추격매수) 성향 | 급등 종목에 뒤늦게 진입하는 경향 | 고점 대비 진입 가격 분포, 급등 직후 거래 비율 |
| 과잉확신 성향 | 과도하게 거래하는 경향 | Turnover rate, 포지션 크기 변동성 |
| 분산투자 성향 | 여러 종목·섹터에 분산하여 투자하는 경향 | 동시 보유 종목 수, 섹터 집중도 |


* **Phase2 (매매 로그 기반 자동 업데이트):** 사용자가 CSV 형식의 매매 기록을 업로드하면, 자가진단 결과를 대체하여 실제 거래 데이터 기반으로 각 성향을 산출합니다. 내부적으로는 Rule-based / Z-score / LSTM Autoencoder를 포함한 앙상블 방식으로 점수를 계산하며, 낮음 / 중간 / 높음으로 변환하여 표시합니다. 이후 매매 기록이 추가될 때마다 지속 갱신됩니다.


### 2. 3계층 앙상블 기반 행동 패턴 분석
각 계층이 독립적으로 이상 점수를 산출하고 가중 합산하여 최종 위험 점수를 도출하는 앙상블 방식을 채택합니다.

```
최종 위험 점수 = 0.3 × Rule Score + 0.3 × Statistical Score + 0.4 × LSTM Score
```
> 가중치는 잠정값이며, 데이터 검증을 거쳐 확정될 예정입니다.

* **1계층 (Personalized Rule-based):** 명확한 규칙 기반으로 단일 거래의 이상 징후를 즉각 탐지합니다.

* **2계층 (Statistical Anomaly):** **Z-Score** 및 **Mahalanobis Distance**를 활용하여, 다변량 데이터(매매 간격, 수익률, 거래량 등)의 상관관계를 고려한 통계적 이상치를 탐지합니다.

* **3계층 (Deep Learning):** **LSTM Autoencoder**를 통해 시계열 시퀀스 속 연속된 행동 패턴을 분석하고, 전형적인 손실 누적 시퀀스와의 유사도를 재구성 오차(Reconstruction Error)로 측정합니다.

### 3. AI 분석 모델 기반 원인 도출 및 맞춤형 매매 분석 리포트 제공
3계층 앙상블이 이상을 탐지한 이후, 사용자 본인의 매매 데이터를 근거로 원인 분석 결과를 제공합니다. 리포트는 다음 세 가지 컨텍스트를 교차하여 구성됩니다.

* **개인 행동 데이터:** 3계층 앙상블 탐지 결과 + Integrated Gradients 기여도
  
* **복합 성향 프로파일:** Phase 1~2에서 산출된 개인 성향 프로파일과의 일치·이탈 분석
  
* **시장 외부 컨텍스트:** 뉴스·공시 API를 통해 해당 거래 시점의 외부 이벤트를 조회하여 참고 정보로 제공

<br>

## 데이터 전략 및 기술 아키텍처

### 데이터 파이프라인 (Data Augmentation)
* **Base Data:** 한국거래소(KRX) 정보데이터시스템을 통해 **실제 국내 주식의 과거 시세 데이터**를 수집하여 현실적인 시장 배경을 구성합니다.
 
* **Synthetic Data:** 실제 시장 흐름 위에 행동재무학 논문 기반의 **비이성적 매매 시나리오를 파이썬 스크립트로 주입**하여, 모델 학습을 위한 시계열 합성 데이터셋을 자체 구축합니다.

### Tech Stack
| 분류 | 기술 |
|------|------|
| Frontend | React, Recharts|
| Backend | FastAPI, Python, PostgreSQL, SQLAlchemy |
| AI / Data | PyTorch (LSTM), Scikit-learn, Integrated Gradients, Pandas, NumPy |
| Collaboration | GitHub, Notion |
| Database | PostgreSQL (Railway)|
| Deployment | Vercel (Frontend), Railway (Backend)|

<br>

## 프로젝트 구조

```
cloud9/
├── frontend/         # React SPA (대시보드·업로드·리포트 UI)
│   └── src/
│       ├── api/          # 백엔드 연동
│       ├── components/   # 공통 UI 컴포넌트
│       └── pages/        # 화면 (Dashboard·Upload·Profiling·Report)
│
├── backend/          # FastAPI 서버 + AI 분석 파이프라인
│   ├── routers/          # API 엔드포인트
│   ├── models/           # 이상 탐지 모델 (Rule·Z-score·LSTM·XAI)
│   ├── pipeline/         # 데이터 처리·분석 파이프라인
│   └── reset_db.py       # 데모용 DB 초기화 유틸
│
├── data/             # 데모용 샘플 매매내역 CSV
├── config/           # 설정 (settings.yaml)
└── doc/              # 기획 문서
```

<br>

## 실행 및 데모

### Backend (FastAPI)
\`\`\`bash
cd backend
pip install -r requirements.txt

# .env 파일에 DATABASE_URL 설정 (Railway 배포 시 자동 주입)
DATABASE_URL=postgresql://...

uvicorn main:app --reload
\`\`\`
Swagger UI: http://localhost:8000/docs

### Frontend (React)
\`\`\`bash
cd frontend
npm install
npm run dev
\`\`\`
로컬 실행 방법과 데모 시연 요령은 [self_demo.md](self_demo.md) 를 참고하세요.

**배포 주소 : https://canary-rust.vercel.app/**

<br>

## 기대 효과 및 학술적 의의

* **시장 예측에서 인간 행동 모델링으로의 패러다임 전환:** 기존의 퀀트 및 AI 금융 연구가 불확실성이 극도로 높은 **시장 가격(Price) 예측**에 매몰되어 있던 한계를 탈피하고, 비교적 패턴화가 명확한 **투자자의 매매 행동 시퀀스**를 딥러닝과 다변량 통계로 모델링했다는 점에서 차별화된 학술적 가치를 지닙니다.
  
* **사회적 가치:** 개인 투자자 비중이 급증하는 시대에, 무분별한 투기 대신 데이터에 기반한 건강한 투자 습관을 형성하는 **객관적인 분석 도구**로서의 역할을 수행합니다.

<br>

## 팀 정보

| 이름 | 역할 | 담당 영역 |
| --- | --- | --- |
| [최은우](https://github.com/suesu1204) | AI / 데이터 / 백엔드 | 3계층 앙상블 모델, XAI, 피처 엔지니어링, 데이터 파이프라인 |
| [박나림](https://github.com/nariming) | 백엔드 | FastAPI 서버, API 설계, DB 스키마 설계, AI 모델 연동 |
| [임도경](https://github.com/ldkxllux) | 프론트엔드 | React 기반 SPA 구현, 대시보드 및 데이터 시각화 (Recharts), FastAPI 연동 |

---
최종수정일 : 2026.06.22
