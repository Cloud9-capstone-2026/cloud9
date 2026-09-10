"""
OpenDART 공시 목록 수집 → dart_disclosures 캐시.

[중요 — mock 대비 실제 데이터 한계] 프론트 mock(data/mock.ts의 dartNews)은
"삼성전자 2026년 2분기 연결 재무제표 기준 영업이익 18.9조원 달성"처럼 내용을
요약한 문장이지만, OpenDART list.json은 report_nm(공시 제목, 예: "분기보고서
(2026.06)", "주요사항보고서(자기주식취득결정)")만 준다 — 본문 요약 API가
아니다. title은 report_nm 그대로 쓴다. 실제 내용 요약을 보여주려면 rcept_no로
원문을 열어 파싱하는 별도 작업이 필요한데(공시 원문은 회사·서식마다 구조가
달라 파싱 난이도가 높음) 이번 범위 밖 — 도경에게 미리 공유 필요.

수집 대상: 최근 N일 전체 공시(특정 종목으로 안 좁힘) — 홈/전체소식은 시장
전체가 맞고, 리포트 상세의 "관련 공시"는 이 캐시를 corp_name으로 필터링해서
쓴다(추가 API 호출 없음).

일 쿼터 1만 콜(OpenDART) — 페이지당 최대 100건, 최근 7일치를 3시간마다
갱신해도 하루 호출 수가 쿼터에 비해 미미하다.
"""
import logging
import os
import re
from datetime import date, datetime, timedelta

import requests

from database import SessionLocal
from orm import DartDisclosure

logger = logging.getLogger(__name__)

DART_LIST_API = "https://opendart.fss.or.kr/api/list.json"
FETCH_DAYS_BACK = 7      # 최근 7일 공시만 수집(오래된 건 갱신 의미 없음)
MAX_PAGES = 5            # 페이지당 100건 × 5 = 최대 500건/회 — 안전 상한
PAGE_COUNT = 100


def _derive_type(report_nm: str) -> str:
    """report_nm에서 배지에 쓸 짧은 유형명 추출.
    예: '주요사항보고서(자기주식취득결정)' → '자기주식취득결정'
        '분기보고서 (2026.06)' → '분기보고서' (괄호 안이 날짜라 유형 아님)
    """
    m = re.search(r"\(([^)]+)\)", report_nm)
    if m and not re.search(r"\d", m.group(1)):
        return m.group(1).strip()
    return re.sub(r"\s*\(.*\)\s*", "", report_nm).strip()


def _fetch_page(api_key: str, bgn_de: str, end_de: str, page_no: int) -> dict:
    r = requests.get(DART_LIST_API, params={
        "crtfc_key": api_key, "bgn_de": bgn_de, "end_de": end_de,
        "page_no": page_no, "page_count": PAGE_COUNT,
        "sort": "date", "sort_mth": "desc",
    }, timeout=10)
    r.raise_for_status()
    return r.json()


def refresh_dart_disclosures() -> int:
    """최근 7일 공시를 받아 신규만 저장. 신규 저장 건수 반환.

    OPENDART_API_KEY 미설정/호출 실패는 전체 배치를 죽이면 안 되므로 경고
    로그만 남기고 0을 반환한다(스케줄러가 다음 주기에 다시 시도).
    """
    api_key = os.environ.get("OPENDART_API_KEY")
    if not api_key:
        logger.warning("OPENDART_API_KEY 미설정 — 공시 수집 스킵")
        return 0

    today = date.today()
    bgn_date = today - timedelta(days=FETCH_DAYS_BACK)
    bgn_de = bgn_date.strftime("%Y%m%d")
    end_de = today.strftime("%Y%m%d")

    db = SessionLocal()
    saved = 0
    try:
        existing_rcept_nos = {
            row.rcept_no for row in db.query(DartDisclosure.rcept_no)
            .filter(DartDisclosure.disclosure_date >= bgn_date).all()
        }
        for page_no in range(1, MAX_PAGES + 1):
            try:
                data = _fetch_page(api_key, bgn_de, end_de, page_no)
            except Exception as e:  # noqa: BLE001 — 네트워크 오류는 이번 회차만 포기
                logger.warning("DART list.json 호출 실패(page=%s): %r", page_no, e)
                break

            status = data.get("status")
            if status == "013":  # 조회된 데이타가 없습니다
                break
            if status != "000":
                logger.warning("DART list.json 응답 오류: status=%s message=%s",
                                status, data.get("message"))
                break

            items = data.get("list") or []
            for item in items:
                rcept_no = item.get("rcept_no")
                if not rcept_no or rcept_no in existing_rcept_nos:
                    continue
                try:
                    disclosure_date = datetime.strptime(item["rcept_dt"], "%Y%m%d").date()
                except (KeyError, ValueError):
                    continue
                report_nm = item.get("report_nm", "").strip()
                db.add(DartDisclosure(
                    rcept_no=rcept_no,
                    corp_name=item.get("corp_name", "")[:100],
                    report_type=_derive_type(report_nm)[:100],
                    title=report_nm[:500],
                    disclosure_date=disclosure_date,
                ))
                existing_rcept_nos.add(rcept_no)
                saved += 1

            if page_no >= int(data.get("total_page", 1)):
                break

        db.commit()
        logger.info("공시 %d건 신규 저장 (최근 %d일)", saved, FETCH_DAYS_BACK)
        return saved
    except Exception as e:  # noqa: BLE001 — 배치 실패가 서버를 죽이면 안 됨
        db.rollback()
        logger.warning("공시 수집 실패: %r", e)
        return saved
    finally:
        db.close()