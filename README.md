# 📈 다중 퀀트 전략 실시간 상태 모니터링 및 AI 기반 이상 징후 탐지 시스템
> **Real-time Multi-Quant Strategy Monitoring & AI-based Anomaly Detection System**

<br>

---
<br>

## 1. 시스템 소개: Canary (카나리아) 🐤
### **"금융 시장의 위험을 가장 먼저 알리는 조기 경보 시스템"**

* **Motivation**: **Canary**는 과거 탄광의 유해 가스를 감지해 광산의 위험을 조기에 알리던 카나리아처럼, 금융 시장에서 발생하는 미세한 이상 징후를 조기에 탐지하고, 투자 전략의 위험 신호를 사용자에게 가장 빠르게 전달하는 것을 목표로 한다.
* **프로젝트 목표**: 실시간 KRX 시장 데이터를 기반으로 복수의 퀀트 전략을 동시에 실행하고, PnL·MDD·Sharpe 등 성과 지표를 실시간 산출하여 전략의 이상 징후를 자동 탐지하는 시스템을 구축한다.

<br>

## 2. 프로젝트 제안 배경 (Problem Definition)
* **판단 지연**: 전략 성과가 비정상적으로 변화하더라도, 원인이 시장 변화 때문인지 전략 자체의 문제인지 즉각 판단하기에 어려움이 있다.
* **모니터링 한계**: 다중 전략 운용 시 전략 간 성과 비교 및 실시간 이상 여부를 감지하는 체계가 부족하여 손실 발생 위험이 존재한다.
* **자동화 필요성**: 시장이 변화함에 따라 기존의 수동 모니터링 방식에서 벗어나, 이상의 원인을 시장 전체 문제와 특정 전략 문제로 자동 구분하는 실시간 시스템에 대한 필요성이 높아지고 있다.

<br>

## 3. 시스템 구조 (System Architecture)
Canary는 데이터 수집부터 이상 탐지, 알림까지 이어지는 **End-to-End 파이프라인**을 제공한다.

<img width="2096" height="204" alt="KakaoTalk_Photo_2026-04-06-17-57-54" src="https://github.com/user-attachments/assets/53382df8-8db6-4fc4-94b1-d39425c4a796" />

<br>

1.  **실시간 시장 데이터**: 실시간 KRX 데이터를 초 단위로 수집 및 처리하는 파이프라인을 구축합.
2.  **전략 실행 엔진**: 이동평균(MA), RSI, 모멘텀 등 복수 전략을 독립된 환경에서 동시 실행.
3.  **메트릭 계산**: 각 전략별 일일 수익률(PnL), 최대 낙폭(MDD), 샤프 비율(Sharpe) 등 성과 지표를 실시간으로 연산.
4.  **3계층 앙상블 이상 탐지 (Core)**: 
    * **1계층 (Rule-based)**: 설정된 리스크 파라미터(손절선 등) 이탈 감지.
    * **2계층 (Statistical)**: Z-score 기반의 통계적 변동성 분석.
    * **3계층 (Machine Learning)**: ML 모델을 통한 비정상 패턴 식별.
5.  **결과 판단**: 탐지 모델의 분석을 통해 현재 전략의 상태를 정상 또는 이상으로 최종 구분하고 이상의 원인을 추정.
6.  **알림 및 시각화**: React 기반 대시보드 시각화 및 WebSocket 기반 실시간 푸시 알림을 제공.

<br>

## 4. 주요 기능 (Main Features)

* **Real-time Engine**: 초 단위 KRX 시장 데이터 스트리밍 및 성과 지표(PnL, MDD, Sharpe) 산출.
* **Hybrid Detection**: Rule-based, Statistical(Z-score), Machine Learning(Isolation Forest 등)을 결합한 3계층 앙상블 탐지.
* **Automatic Root Cause Analysis**: 이상 발생 시 시장 요인과 전략 요인을 분리 분석하여 원인 추정.
* **Interactive Dashboard**: 전략별 성과 차트와 이상 이력을 한눈에 볼 수 있도록 시각화, WebSocket 기반의 실시간 차트 업데이트 및 긴급 리스크 푸시 알림.
  
<br>

## 5. 적용 기술 (Technical Stack)
| 구분 | 상세 기술 |
| :--- | :--- |
| **Frontend** | React, Recharts (성과 시각화), WebSocket client |
| **Backend** | Python, FastAPI, SQLAlchemy (DB), WebSocket |
| **AI/Data** | Pandas, NumPy, Scikit-learn (3계층 앙상블 탐지 모델) |
| **Infrastructure** | Cloud Hosting, 고성능 GPU 워크스테이션 |
| **Collaboration** | GitHub, Notion (프로젝트 문서화)  |

<br>

## 📂 프로젝트 구조 (Project Structure)

본 프로젝트는 모듈화된 아키텍처로 전략 수립, 데이터 수집, 이상 탐지 로직을 분리해서 관리한다.

```text
cloud9/
├── main.py                # 시스템 통합 실행 엔트리 포인트
├── token.dat              # API 인증 토큰 관리 파일
│
├── broker/                # 데이터 수집 및 거래 인터페이스
│   └── korea_investment.py # 한국투자증권 API 연동 및 실시간 시세 수집
│
├── strategy/              # 퀀트 매매 전략 모듈
│   ├── base.py            # 전략 추상화를 위한 기본 클래스
│   ├── ma_crossover.py    # 이동평균 크로스오버 전략 로직
│   └── rsi.py             # RSI 지표 기반 매매 전략 로직
│
├── portfolio/             # 자산 및 성과 관리 모듈
│   └── portfolio.py       # 실시간 PnL, MDD 계산 및 포지션 관리
│
└── detector/              # 3계층 하이브리드 이상 탐지 엔진
    ├── rule.py            # 1계층: 사전 정의된 임계치 기반 Rule 탐지
    ├── zscore.py          # 2계층: 통계적 변동성 기반 Z-score 탐지
    └── lstm.py            # 3계층: AI(LSTM) 기반 비정상 패턴 탐지
```

<br>

## 6. 기대효과 및 실익 (Value Proposition)

본 프로젝트는 기술적 고도화와 실무적 활용성을 결합하여 다음과 같은 비즈니스 가치를 창출한다.

* **리스크 대응 속도 향상 및 손실 최소화**: 수동 모니터링 자동화를 통해 이상 징후를 조기에 포착하고 신속하게 대응하여 손실 최소화 가능.
* **운용 안정성 확보**: 시장과 전략의 문제를 즉각 구분하여 불필요한 전략 수정을 방지하고 리스크 관리 효율 극대화.
* **높은 탐지 신뢰도**: 3계층 앙상블 방식을 통해 단일 방식 대비 오분류율을 낮추고 탐지 성공률 95% 이상을 목표.

<br>

## 7. 팀 정보
* **팀명**: Cloud9 (TEAM 09)
* **지도교수**: 이민수 교수님
* **팀원**: 박나림, 임도경, 최은우
* **Repo**: [https://github.com/Cloud9-capstone-2026](https://github.com/Cloud9-capstone-2026)
* **Ground Rule**: [Team Ground Rule](https://github.com/Cloud9-capstone-2026/cloud9/blob/main/Team_Ground_Rule.md)

---
 최종수정일 : 2026.04.09
