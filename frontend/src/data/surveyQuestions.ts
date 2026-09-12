import type { BiasKey } from '../theme/tokens';

export interface SurveyQuestion {
  id: string;
  axis: BiasKey;
  reverse: boolean;
  text: string;
}

// 백엔드 제출 스펙(question_id 문자열, 예: "ds_1") 그대로 — 화면 표시 순서는 매 검사 시작마다
// 셔플되지만, 이 배열 자체(=원본 순서·id)는 절대 바뀌지 않는다.
export const SURVEY_QUESTIONS: SurveyQuestion[] = [
  { id: 'ds_1', axis: 'disposition_strength', reverse: false, text: '수익이 조금이라도 나면, 더 오를 수 있어도 일단 팔아서 이익을 확정하고 싶다.' },
  { id: 'ds_2', axis: 'disposition_strength', reverse: false, text: '손실 중인 종목은 손실을 확정하기 싫어서 계속 들고 있는 편이다.' },
  { id: 'ds_3', axis: 'disposition_strength', reverse: false, text: '나는 오른 종목보다 내린 종목을 더 오래 보유하는 경향이 있다.' },
  { id: 'ds_4', axis: 'disposition_strength', reverse: false, text: '손실이 나면 "다시 오를 때까지 기다리자"고 스스로를 설득하곤 한다.' },
  { id: 'ds_5', axis: 'disposition_strength', reverse: true, text: '목표 수익률에 도달하지 않았어도, 손실 여부와 상관없이 계획한 시점에 매도하는 편이다.' },

  { id: 'oc_1', axis: 'overconfidence', reverse: false, text: '내 투자 판단은 대체로 다른 투자자들보다 정확하다고 생각한다.' },
  { id: 'oc_2', axis: 'overconfidence', reverse: false, text: '수익이 났을 때는 내 실력이나 분석 덕분이라고 생각하는 편이다.' },
  { id: 'oc_3', axis: 'overconfidence', reverse: false, text: '손실이 났을 때는 운이 나빴거나 시장 상황 탓이라고 생각하는 편이다.' },
  { id: 'oc_4', axis: 'overconfidence', reverse: false, text: '주가가 오르는 시기엔 평소보다 더 자주 거래하고 싶어진다.' },
  { id: 'oc_5', axis: 'overconfidence', reverse: true, text: '내가 잘 안다고 생각하는 종목이라도, 내 판단이 틀릴 수 있다고 자주 생각한다.' },

  { id: 'lp_1', axis: 'lottery_preference', reverse: false, text: '적은 돈으로 크게 오를 수 있는 종목에 끌린다.' },
  { id: 'lp_2', axis: 'lottery_preference', reverse: false, text: '주가가 낮은 종목(이른바 "동전주")에 관심이 가는 편이다.' },
  { id: 'lp_3', axis: 'lottery_preference', reverse: false, text: '하루 만에 급등할 것 같은 종목을 종종 매수한다.' },
  { id: 'lp_4', axis: 'lottery_preference', reverse: false, text: '안정적으로 조금씩 오르는 종목보다 크게 오르내리는 종목이 더 흥미롭다.' },
  { id: 'lp_5', axis: 'lottery_preference', reverse: false, text: '여러 종목에 나눠 투자하기보다 소수 종목에 집중하는 편이다.' },

  { id: 'hs_1', axis: 'herd_sensitivity', reverse: false, text: '요즘 화제가 되는(뉴스·커뮤니티에서 많이 언급되는) 종목이면 나도 사보고 싶어진다.' },
  { id: 'hs_2', axis: 'herd_sensitivity', reverse: false, text: '다른 사람들이 많이 사는 종목을 보면 나도 사야 할 것 같은 기분이 든다.' },
  { id: 'hs_3', axis: 'herd_sensitivity', reverse: false, text: '급등 중인 종목을 보면 놓칠까봐 따라서 매수한 적이 있다.' },
  { id: 'hs_4', axis: 'herd_sensitivity', reverse: false, text: '커뮤니티나 지인이 추천한 종목을 스스로 분석하지 않고 매수한 적이 있다.' },
  { id: 'hs_5', axis: 'herd_sensitivity', reverse: true, text: '다른 사람들이 어떤 종목을 사고팔든 내 투자 결정에는 영향을 주지 않는다.' },
];

// Fisher-Yates — 매 검사 시작마다 호출해서 "화면에 보여줄 순서"만 새로 만든다.
// 원본 SURVEY_QUESTIONS와 각 문항의 id는 절대 바뀌지 않는다.
export function shuffleQuestions(): SurveyQuestion[] {
  const arr = SURVEY_QUESTIONS.slice();
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}
