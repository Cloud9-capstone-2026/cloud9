# 🐤 Canary <br> : 반복적인 손실을 겪는 개인 주식 투자자를 위한 <br> AI 기반 매매 행동 분석 및 맞춤형 투자 습관 개선 플랫폼

> **"시장을 분석하는 것이 아니라, 나 자신을 분석한다."**

<br>

## 프로젝트 소개
 
Canary는 개인 주식 투자자의 매매 로그를 AI로 분석하여 비이성적 행동 패턴을 자동으로 탐지하고, 손실의 원인을 데이터 기반으로 설명하여 투자자 스스로 자신의 습관을 인지하고 개선할 수 있도록 올바른 투자 방향을 제시하는 시스템입니다.
 
투자자의 실패 원인을 '정보 부족'이 아닌 '행동 통제 실패'에서 찾고, 객관적인 데이터 분석과 맞춤형 투자 습관 개선 솔루션을 통해 실질적인 손실 방어와 건강한 투자 습관을 형성을 지원합니다.

<br>

## 프로젝트 배경 및 문제 정의

### 왜 대다수의 개인 투자자는 시장에서 패배하는가?

* **정보의 문제가 아닌 행동의 문제:** 국내 개인 투자자 수가 역대 최고치를 기록하고 있으나, 대다수가 명확한 기준 없이 FOMO, 패닉셀 등 비이성적 심리에 기반한 매매로 손실을 반복합니다.
  
* **기존 서비스의 한계:** 대부분의 플랫폼은 "무엇을 살 것인가(What to buy)"에만 집중할 뿐, 정작 투자 실패의 핵심인 "나는 왜 잃는가(Why I lose)"에 대한 답을 주지 못합니다.

### Canary의 해결책
Canary는 수익 창출이 아닌, '손실을 유발하는 행동'을 줄이는 데 집중합니다. 사용자의 매매 데이터 분석을 통해 무의식중에 반복되는 비이성적 패턴을 객관적으로 식별하여 손실 원인을 스스로 이해하고 투자 습관을 개선할 수 있도록 지원합니다. 장기적으로 사용자의 실질적인 손실 방어 및 건전한 투자 습관 형성을 유도합니다.

<br>

## 주요 기능 (Key Features)

### 1. 투자자 페르소나 진단
* 사용자의 매매 데이터를 분석하여 행동재무학 관점의 투자자 페르소나(추격매수형, 손절불가형 등)를 도출합니다.
* **동적 프로파일링:** 초기 진단에 그치지 않고, 매매 데이터가 축적됨에 따라 페르소나를 주기적으로 업데이트하여 변화하는 투자 습관을 추적합니다.

### 2. 3계층 앙상블 기반 행동 패턴 분석
* **1계층 (Personalized Rule-based):** 개인의 평소 매매 빈도 및 진입 타이밍을 기준으로 동적 임계값을 설정하여 이상 징후를 1차 필터링합니다.
* **2계층 (Statistical Anomaly):** **Z-Score** 및 **Mahalanobis Distance**를 활용하여, 다변량 데이터(매매 간격, 수익률, 거래량 등)의 상관관계를 고려한 통계적 이상치를 탐지합니다.
* **3계층 (Deep Learning):** **LSTM Autoencoder**를 통해 전형적인 손실 누적 패턴과 현재 패턴과의 유사도를 분석하여 비정상적인 매매 시퀀스 패턴을 최종적으로 식별합니다.

### 3. AI 분석 모델 기반 행동 원인 도출 및 맞춤형 솔루션 제공
* **역맵핑(Reverse Mapping) 기술:** Integrated Gradients로 산출한 주요 Feature 기여도를 행동재무학 이론과 연결하여 "손실 복구 심리(40%)", "고점 추격(35%)" 등 유저가 이해하기 쉬운 자연어 리포트를 생성합니다.
* **강력한 가드레일:** 단순히 경고를 주는 것을 넘어, "손실 발생 후 20분간 매수 제한"과 같은 구체적인 행동 가이드를 제공합니다.

<br>

## 데이터 전략 및 기술 아키텍처

### 데이터 파이프라인 (Data Augmentation)
* **Base Data:** 한국거래소(KRX) 정보데이터시스템 등을 통해 **실제 국내 주식의 과거 시세 데이터**를 수집하여 현실적인 시장 배경을 구성합니다.
* **Synthetic Data:** 실제 시장 흐름 위에 행동재무학 논문 기반의 **비이성적 매매 시나리오를 파이썬 스크립트로 주입**하여, 모델 학습을 위한 시계열 합성 데이터셋을 자체 구축합니다.

### Tech Stack
| 분류 | 기술 |
|------|------|
| Frontend | React, Recharts, WebSocket |
| Backend | FastAPI, Python |
| AI / Data | PyTorch (LSTM), Scikit-learn, Integrated Gradients, Pandas, NumPy |
| Collaboration | GitHub, Notion |

<br>

## 프로젝트 구조

```
canary/
├── data/
│   ├── raw/              # 원본 거래 로그 CSV
│   ├── processed/        # 피처 추출 결과
│   ├── market/           # 시장 OHLCV 데이터 (yfinance / KRX)
│   └── synthetic/        # 행동재무학 기반 합성 데이터
│
├── models/
│   ├── rule_based.py     # Layer 1 — 규칙 기반 탐지 (고점추격, 과회전율)
│   ├── zscore.py         # Layer 2 — Z-Score · Mahalanobis 통계 탐지
│   ├── lstm_ae.py        # Layer 3 — LSTM Autoencoder
│   ├── xai.py            # Integrated Gradients → 피처 기여도 산출
│   └── persona.py        # 투자 성향 클러스터링
│
├── pipeline/
│   ├── ingest.py         # 거래 로그 로드 + 시장 데이터 병합
│   ├── feature_eng.py    # PGR/PLR, Turnover, 모멘텀 추격률 계산
│   ├── detect.py         # 3계층 앙상블 순차 실행
│   └── coach.py          # XAI 결과 → 자연어 코칭 리포트 생성
│
├── api/
│   ├── main.py           # FastAPI 앱 진입점
│   ├── routes.py         # 엔드포인트 정의
│   └── schemas.py        # Pydantic 입출력 모델
│
├── reports/              # 생성된 코칭 리포트 (JSON)
│
├── notebooks/
│   ├── 01_eda.ipynb      # 탐색적 데이터 분석
│   └── 02_lstm_train.ipynb  # LSTM AE 학습 실험
│
└── config/
    └── settings.yaml     # 임계값 및 하이퍼파라미터
```

### 핵심 선행 연구

| 논문 | 연결 컴포넌트 |
|------|-------------|
| Odean (1998) — 처분 효과 | `feature_eng.py` PGR/PLR 산출 |
| Barber & Odean (2001) — 과잉확신·회전율 | `feature_eng.py` Turnover |
| Grinblatt et al. (1995) — 모멘텀 추격 | `rule_based.py` 1계층 규칙 |
| Kahneman & Tversky (1979) — 전망이론 | `xai.py` 손실 회피 매핑 |
| Jing et al. (2021) — LSTM 하이브리드 | `lstm_ae.py` 아키텍처 |
| Ozbayoglu et al. (2020) — 딥러닝 금융 이상탐지 | `lstm_ae.py` 학습 전략 |
| Shantha (2019) — 페르소나 분류 | `persona.py` 클러스터링 |
| Şeker et al. (2025) — AI 행동재무학 리뷰 | 전체 시스템 이론적 근거 |

<br>

## 기대 효과 및 학술적 의의

* **시장 예측에서 인간 행동 모델링으로의 패러다임 전환:** 기존의 퀀트 및 AI 금융 연구가 불확실성이 극도로 높은 **시장 가격(Price) 예측**에 매몰되어 있던 한계를 탈피하고, 비교적 패턴화가 명확한 **투자자의 매매 행동 시퀀스**를 딥러닝과 다변량 통계로 모델링했다는 점에서 차별화된 학술적 가치를 지닙니다.
  
* **사회적 가치:** 개인 투자자 비중이 급증하는 시대에, 무분별한 투기 대신 데이터에 기반한 건강한 투자 습관을 형성하는 **디지털 행동 가이드** 역할을 수행합니다.

<br>

## 👥 팀 정보

* **팀명**: Cloud9 (TEAM 09)
* **지도교수**: 이민수 교수님
* **팀원**: 박나림, 임도경, 최은우
* **Repo**: [https://github.com/Cloud9-capstone-2026](https://github.com/Cloud9-capstone-2026)
* **Ground Rule**: [Team Ground Rule](https://github.com/Cloud9-capstone-2026/cloud9/blob/main/Team_Ground_Rule.md)

---
최종수정일 : 2026.05.05
