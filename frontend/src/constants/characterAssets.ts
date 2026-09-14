import type { ImageSourcePropType } from 'react-native';

export type TypeCode =
  | 'HHHH' | 'HHHL' | 'HHLH' | 'HHLL'
  | 'HLHH' | 'HLHL' | 'HLLH' | 'HLLL'
  | 'LHHH' | 'LHHL' | 'LHLH' | 'LHLL'
  | 'LLHH' | 'LLHL' | 'LLLH' | 'LLLL';

export interface CharacterInfo {
  code: TypeCode;
  name: string;
  // 16종 전부 실제 이미지가 있음(null은 UNKNOWN_CHARACTER 전용) — 컴포넌트 쪽에서
  // null이면 공용 Avatar로 대체 표시.
  image: ImageSourcePropType | null;
}

const NAMES: Record<TypeCode, string> = {
  HHHH: '저돌적인 승부사형',
  HHHL: '소신있는 승부사형',
  HHLH: '확신에 찬 동조형',
  HHLL: '고집스런 확신형',
  HLHH: '불안한 동조형',
  HLHL: '조용한 몽상가형',
  HLLH: '조심스런 동조형',
  HLLL: '신중한 홀더형',
  LHHH: '화려한 트렌드형',
  LHHL: '고독한 승부사형',
  LHLH: '당당한 대세형',
  LHLL: '결단력있는 전략가형',
  LLHH: '발빠른 대세 편승형',
  LLHL: '홀로 도전하는 모험가형',
  LLLH: '안전한 동행형',
  LLLL: '차분한 전략가형',
};

// RN/Metro는 동적 경로로 require()를 못 해서 16개를 직접 나열한다.
const IMAGES: Record<TypeCode, ImageSourcePropType> = {
  HHHH: require('../assets/characters/HHHH.png'),
  HHHL: require('../assets/characters/HHHL.png'),
  HHLH: require('../assets/characters/HHLH.png'),
  HHLL: require('../assets/characters/HHLL.png'),
  HLHH: require('../assets/characters/HLHH.png'),
  HLHL: require('../assets/characters/HLHL.png'),
  HLLH: require('../assets/characters/HLLH.png'),
  HLLL: require('../assets/characters/HLLL.png'),
  LHHH: require('../assets/characters/LHHH.png'),
  LHHL: require('../assets/characters/LHHL.png'),
  LHLH: require('../assets/characters/LHLH.png'),
  LHLL: require('../assets/characters/LHLL.png'),
  LLHH: require('../assets/characters/LLHH.png'),
  LLHL: require('../assets/characters/LLHL.png'),
  LLLH: require('../assets/characters/LLLH.png'),
  LLLL: require('../assets/characters/LLLL.png'),
};

export const CHARACTERS: Record<TypeCode, CharacterInfo> = Object.fromEntries(
  (Object.keys(NAMES) as TypeCode[]).map((code) => [code, { code, name: NAMES[code], image: IMAGES[code] }])
) as Record<TypeCode, CharacterInfo>;

const UNKNOWN_CHARACTER: CharacterInfo = { code: 'HHHH', name: '알 수 없는 유형', image: null };

// 매핑에 없는 type_code(오타·서버가 새로 추가한 조합 등)가 와도 앱이 죽지 않고
// 안전한 기본값으로 대체 — 4번 요구사항.
export function getCharacter(typeCode: string): CharacterInfo {
  return (CHARACTERS as Record<string, CharacterInfo>)[typeCode] ?? UNKNOWN_CHARACTER;
}
