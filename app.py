import streamlit as st
import json
import os
import calendar
from datetime import datetime, timedelta, date

# ----------------- 구글 시트 연동 헬퍼 -----------------
LOCAL_DATA_FILE = "data.json"

def get_default_data():
    t_date = datetime.now().date()
    return {
        "schedules": [
            {
                "id": 1,
                "title": "물리약학2",
                "type": "보강",
                "professor": "담당교수",
                "date": t_date.strftime("%Y-%m-%d"),
                "end_date": t_date.strftime("%Y-%m-%d"),
                "is_range": False,
                "start_period": 3,
                "end_period": 3,
                "building": "A3관",
                "room_detail": "202호",
                "room": "A3관 202호",
                "memo": "계산기 지참"
            },
            {
                "id": 2,
                "title": "약품생화학2",
                "type": "휴강",
                "professor": "담당교수",
                "date": (t_date + timedelta(days=2)).strftime("%Y-%m-%d"),
                "end_date": (t_date + timedelta(days=2)).strftime("%Y-%m-%d"),
                "is_range": False,
                "start_period": 6,
                "end_period": 7,
                "building": "A3관",
                "room_detail": "202호",
                "room": "A3관 202호",
                "memo": "학회 참석"
            }
        ],
        "notes": [
            {
                "id": 1,
                "title": "실험복 공동구매 건",
                "category": "업무",
                "content": "사이즈 취합 마감 및 업체 견적 확인",
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
        ]
    }

def get_gspread_client():
    if "gcp_service_account" in st.secrets and "SPREADSHEET_ID" in st.secrets:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(st.secrets["SPREADSHEET_ID"]).sheet1
        return sheet
    return None

def load_data():
    sheet = get_gspread_client()
    # 1. 구글 시트 연결 환경인 경우
    if sheet:
        try:
            val = sheet.cell(1, 1).value
            if val:
                return json.loads(val)
            else:
                default_data = get_default_data()
                sheet.update_cell(1, 1, json.dumps(default_data, ensure_ascii=False))
                return default_data
        except Exception:
            default_data = get_default_data()
            return default_data

    # 2. 로컬 테스트 환경 (data.json 사용)
    if not os.path.exists(LOCAL_DATA_FILE):
        d = get_default_data()
        save_data(d)
        return d
    try:
        with open(LOCAL_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        d = get_default_data()
        save_data(d)
        return d

def save_data(data):
    sheet = get_gspread_client()
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    # 구글 시트에 업데이트
    if sheet:
        try:
            sheet.update_cell(1, 1, json_str)
            return
        except Exception as e:
            st.error(f"구글 시트 저장 중 오류: {e}")

    # 로컬 파일에 백업 저장
    with open(LOCAL_DATA_FILE, "w", encoding="utf-8") as f:
        f.write(json_str)

# ----------------- 시간표 팝업용 HTML 생성 -----------------
def generate_timetable_html():
    days = ["월", "화", "수", "목", "금"]
    grid = [[{"name": "", "span": 1, "skip": False} for _ in range(5)] for _ in range(9)]

    for d_idx, day_name in enumerate(days):
        for course in TIMETABLE_2026_2[day_name]:
            start_p = course["start"] - 1
            end_p = course["end"] - 1
            span = end_p - start_p + 1
            grid[start_p][d_idx] = {"name": course["name"], "span": span, "skip": False}
            for p in range(start_p + 1, end_p + 1):
                grid[p][d_idx]["skip"] = True

    html = """
    <style>
        .tt-table { width: 100%; border-collapse: collapse; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; text-align: center; }
        .tt-table th, .tt-table td { border: 1px solid #dadce0; padding: 6px 4px; font-size: 0.85rem; }
        .tt-table th { background-color: #f8f9fa; font-weight: 600; color: #3c4043; }
        .tt-cell-major { background-color: #f8bbd0; color: #111; font-weight: 600; }
        .tt-cell-elective { background-color: #ffffff; color: #3c4043; font-weight: 500; }
        .tt-cell-empty { background-color: #ffffff; }
    </style>
    <table class="tt-table">
        <thead>
            <tr>
                <th style="width: 8%;">교시</th>
                <th style="width: 18.4%;">월</th>
                <th style="width: 18.4%;">화</th>
                <th style="width: 18.4%;">수</th>
                <th style="width: 18.4%;">목</th>
                <th style="width: 18.4%;">금</th>
            </tr>
        </thead>
        <tbody>
    """
    for p in range(9):
        p_num = p + 1
        html += f"<tr><td style='background-color: #f8f9fa; font-weight: bold; color: #5f6368;'>{p_num}</td>"
        for d in range(5):
            cell = grid[p][d]
            if cell["skip"]:
                continue
            if cell["name"]:
                c_name = cell["name"]
                cell_class = "tt-cell-elective" if ("(전선)" in c_name or "1학년" in c_name) else "tt-cell-major"
                html += f"<td rowspan='{cell['span']}' class='{cell_class}'>{c_name}</td>"
            else:
                html += "<td class='tt-cell-empty'></td>"
        html += "</tr>"
    html += "</tbody></table>"
    return html

@st.dialog("🗓️ 2026-2 정규 강의 시간표", width="large")
def show_timetable_modal():
    st.markdown(generate_timetable_html(), unsafe_allow_html=True)
    st.caption("※ 분홍색: 전공필수 | 흰색: 전공선택(전선) 및 1학년 과목")

# ----------------- 교시 시간 매핑 -----------------
PERIOD_TIMES = {
    1: ("09:00", "09:50"),
    2: ("10:00", "10:50"),
    3: ("11:00", "11:50"),
    4: ("12:00", "12:50"),
    5: ("13:00", "13:50"),
    6: ("14:00", "14:50"),
    7: ("15:00", "15:50"),
    8: ("16:00", "16:50"),
    9: ("17:00", "17:50"),
    10: ("18:00", "18:50"),
}

# ----------------- 데이터 로드 및 저장 -----------------
def get_default_data():
    t_date = datetime.now().date()
    return {
        "schedules": [
            {
                "id": 1,
                "title": "물리약학2",
                "type": "보강",
                "professor": "담당교수",
                "date": t_date.strftime("%Y-%m-%d"),
                "end_date": t_date.strftime("%Y-%m-%d"),
                "is_range": False,
                "start_period": 3,
                "end_period": 3,
                "building": "A3관",
                "room_detail": "202호",
                "room": "A3관 202호",
                "memo": "계산기 지참"
            },
            {
                "id": 2,
                "title": "약품생화학2",
                "type": "휴강",
                "professor": "담당교수",
                "date": (t_date + timedelta(days=2)).strftime("%Y-%m-%d"),
                "end_date": (t_date + timedelta(days=2)).strftime("%Y-%m-%d"),
                "is_range": False,
                "start_period": 6,
                "end_period": 7,
                "building": "A3관",
                "room_detail": "202호",
                "room": "A3관 202호",
                "memo": "학회 참석"
            }
        ],
        "notes": [
            {
                "id": 1,
                "title": "실험복 공동구매 건",
                "category": "업무",
                "content": "사이즈 취합 마감 및 업체 견적 확인",
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
        ]
    }

def load_data():
    if not os.path.exists(DATA_FILE):
        d = get_default_data()
        save_data(d)
        return d
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for s in data.get("schedules", []):
            if "date" not in s:
                s["date"] = s.get("start", datetime.now().strftime("%Y-%m-%d"))[:10]
            if "end_date" not in s:
                s["end_date"] = s["date"]
            if "start_period" not in s:
                s["start_period"] = 1
            if "end_period" not in s:
                s["end_period"] = 2
            if "room" not in s:
                s["room"] = "A3관 202호"
            if "is_range" not in s:
                s["is_range"] = (s.get("type") == "기타" and s.get("end_date") != s["date"])
        return data
    except Exception:
        d = get_default_data()
        save_data(d)
        return d

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

st.set_page_config(page_title="2026-2 학사 일정 포털", layout="wide", page_icon="📅")

if "app_data" not in st.session_state:
    st.session_state.app_data = load_data()

today = datetime.now().date()
if "current_year" not in st.session_state:
    st.session_state.current_year = today.year
if "current_month" not in st.session_state:
    st.session_state.current_month = today.month
if "selected_date" not in st.session_state:
    st.session_state.selected_date = today

if "inp_title" not in st.session_state:
    st.session_state.inp_title = ""
if "form_start_period" not in st.session_state:
    st.session_state.form_start_period = 1
if "form_end_period" not in st.session_state:
    st.session_state.form_end_period = 2

if "editing_schedule_id" not in st.session_state:
    st.session_state.editing_schedule_id = None
if "editing_note_id" not in st.session_state:
    st.session_state.editing_note_id = None

# 상단 공지 복사 확인창용 상태
if "active_notice_text" not in st.session_state:
    st.session_state.active_notice_text = ""

def on_start_period_change():
    if st.session_state.form_end_period < st.session_state.form_start_period:
        st.session_state.form_end_period = st.session_state.form_start_period

def on_edit_start_period_change():
    if st.session_state.edit_end_period < st.session_state.edit_start_period:
        st.session_state.edit_end_period = st.session_state.edit_start_period

# ----------------- 사이드바: 메모 관리 -----------------
with st.sidebar:
    st.header("📝 개인 메모장")
    
    if st.session_state.editing_note_id is not None:
        target_note = next((n for n in st.session_state.app_data.get("notes", []) if n.get("id") == st.session_state.editing_note_id), None)
        if not target_note:
            st.session_state.editing_note_id = None
            st.rerun()

        with st.container(border=True):
            st.subheader("✏️ 메모 수정")
            cat_list = ["할 일", "학사", "업무", "아이디어", "기타"]
            cur_cat = target_note.get("category", "할 일")
            cat_idx = cat_list.index(cur_cat) if cur_cat in cat_list else 0
            
            e_cat = st.selectbox("분류", cat_list, index=cat_idx, key="edit_note_cat")
            e_title = st.text_input("제목", value=target_note.get("title", ""), key="edit_note_title")
            e_content = st.text_area("내용", value=target_note.get("content", ""), height=120, key="edit_note_content")
            
            c_save, c_cancel = st.columns(2)
            with c_save:
                if st.button("수정 저장", type="primary", use_container_width=True):
                    if not e_title:
                        st.error("제목을 입력해주세요.")
                    else:
                        target_note["category"] = e_cat
                        target_note["title"] = e_title
                        target_note["content"] = e_content
                        target_note["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                        save_data(st.session_state.app_data)
                        st.session_state.editing_note_id = None
                        st.success("메모가 수정되었습니다.")
                        st.rerun()
            with c_cancel:
                if st.button("수정 취소", use_container_width=True):
                    st.session_state.editing_note_id = None
                    st.rerun()
    else:
        with st.expander("➕ 새 메모 작성", expanded=False):
            with st.form("sidebar_note_form", clear_on_submit=True):
                n_cat = st.selectbox("분류", ["할 일", "학사", "업무", "아이디어", "기타"])
                n_title = st.text_input("제목")
                n_content = st.text_area("내용", height=100)
                if st.form_submit_button("저장"):
                    if n_title:
                        new_id = max([n.get("id", 0) for n in st.session_state.app_data.get("notes", [])], default=0) + 1
                        st.session_state.app_data.setdefault("notes", []).append({
                            "id": new_id,
                            "title": n_title,
                            "category": n_cat,
                            "content": n_content,
                            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
                        save_data(st.session_state.app_data)
                        st.rerun()

    st.divider()
    notes = st.session_state.app_data.get("notes", [])
    if not notes:
        st.caption("작성된 메모가 없습니다.")
    else:
        for n in reversed(notes):
            with st.container(border=True):
                st.markdown(f"**[{n.get('category')}] {n.get('title')}**")
                st.write(n.get("content"))
                st.caption(f"🕒 {n.get('updated_at')}")
                
                n_c1, n_c2 = st.columns(2)
                with n_c1:
                    if st.button("✏️ 수정", key=f"edit_note_btn_{n.get('id')}", use_container_width=True):
                        st.session_state.editing_note_id = n.get("id")
                        st.rerun()
                with n_c2:
                    if st.button("🗑️ 삭제", key=f"del_note_{n.get('id')}", use_container_width=True):
                        st.session_state.app_data["notes"] = [x for x in notes if x.get("id") != n.get("id")]
                        if st.session_state.editing_note_id == n.get("id"):
                            st.session_state.editing_note_id = None
                        save_data(st.session_state.app_data)
                        st.rerun()

# ----------------- 메인 상단: 제목 & 알림 위젯 -----------------
all_schedules = st.session_state.app_data.get("schedules", [])

upcoming_events = []
for s in all_schedules:
    try:
        s_dt = datetime.strptime(s["date"], "%Y-%m-%d").date()
        e_dt = datetime.strptime(s.get("end_date", s["date"]), "%Y-%m-%d").date()
        if e_dt >= today and (s_dt - today).days <= 30:
            diff = (s_dt - today).days
            upcoming_events.append((diff, s_dt, e_dt, s))
    except Exception:
        continue

upcoming_events.sort(key=lambda x: (x[0], x[3].get("start_period", 1)))

head_col_left, head_col_right = st.columns([5, 5])

with head_col_left:
    st.title("📅 학사 일정 캘린더")
    st.caption(f"오늘: {today.strftime('%Y년 %m월 %d일 (%a)')}")
    
    if st.button("🔎 2026-2 정규 시간표 팝업으로 보기", type="secondary"):
        show_timetable_modal()

    # 상단 복사 요청 시 원클릭 복사 박스 노출 (우측 상단 복사 아이콘 제공)
    if st.session_state.active_notice_text:
        with st.container(border=True):
            c_top1, c_top2 = st.columns([8, 2])
            with c_top1:
                st.markdown("📋 **아래 박스 우측 상단의 아이콘을 누르면 복사됩니다:**")
            with c_top2:
                if st.button("닫기", use_container_width=True):
                    st.session_state.active_notice_text = ""
                    st.rerun()
            st.code(st.session_state.active_notice_text, language="text")

with head_col_right:
    with st.container(border=True):
        header_top, filter_col = st.columns([3, 3])
        with header_top:
            st.markdown("##### 🔔 **다가오는 일정**")
        with filter_col:
            filter_mode = st.pills(
                "필터",
                options=["전체", "D-7"],
                default="전체",
                label_visibility="collapsed"
            )

        filtered_events = upcoming_events
        if filter_mode == "D-7":
            filtered_events = [x for x in upcoming_events if x[0] <= 7]

        with st.container(height=260):
            if not filtered_events:
                st.caption("해당 조건의 일정이 없습니다.")
            else:
                for diff, s_dt, e_dt, ev in filtered_events:
                    if diff < 0 and e_dt >= today:
                        d_badge = ":blue[**[진행중]**]"
                    elif diff == 0:
                        d_badge = ":red[**[D-Day]**]"
                    elif diff == 1:
                        d_badge = ":orange[**[D-1]**]"
                    else:
                        d_badge = f":gray[**[D-{diff}]**]"

                    ev_type = ev.get("type", "일정")
                    type_colors = {
                        "보강": "red", "휴강": "violet", "시험": "red",
                        "과제": "green", "강의실변경": "orange", "정규강의": "blue", "기타": "teal"
                    }
                    badge_color = type_colors.get(ev_type, "gray")
                    
                    is_range = ev.get("is_range", False)
                    if is_range:
                        date_sub = f"📅 {s_dt.strftime('%m/%d')} ~ {e_dt.strftime('%m/%d')}"
                    else:
                        sp = ev.get("start_period", 1)
                        ep = ev.get("end_period", sp)
                        p_text = f"{sp}~{ep}교시" if sp != ep else f"{sp}교시"
                        date_sub = f"📅 {s_dt.strftime('%m/%d')} ({p_text})"

                    with st.container(border=True):
                        c_text, c_btn1, c_btn2 = st.columns([6, 2, 2])
                        with c_text:
                            st.markdown(f"{d_badge} :{badge_color}[**[{ev_type}]**] **{ev.get('title')}**")
                            st.caption(f"{date_sub} | 📍 {ev.get('room', '-')}")
                        
                        with c_btn1:
                            if st.button("🔍 보기", key=f"view_nav_{ev.get('id')}", use_container_width=True):
                                st.session_state.current_year = s_dt.year
                                st.session_state.current_month = s_dt.month
                                st.session_state.selected_date = s_dt
                                st.rerun()
                        
                        with c_btn2:
                            if st.button("📋 복사", key=f"copy_quick_{ev.get('id')}", use_container_width=True):
                                if is_range:
                                    notice = (
                                        f"📢 [{ev_type}] {ev.get('title')}\n"
                                        f"- 기간: {s_dt.strftime('%Y-%m-%d')} ~ {e_dt.strftime('%Y-%m-%d')}\n"
                                        f"- 장소: {ev.get('room', '-')}"
                                    )
                                else:
                                    sp = ev.get("start_period", 1)
                                    ep = ev.get("end_period", sp)
                                    p_text = f"{sp}~{ep}교시" if sp != ep else f"{sp}교시"
                                    start_clock = PERIOD_TIMES.get(sp, ("09:00", "09:50"))[0]
                                    end_clock = PERIOD_TIMES.get(ep, ("17:00", "17:50"))[1]
                                    notice = (
                                        f"📢 [{ev_type}] {ev.get('title')}\n"
                                        f"- 일시: {s_dt.strftime('%Y-%m-%d')} {p_text} ({start_clock}~{end_clock})\n"
                                        f"- 장소: {ev.get('room', '-')}"
                                    )
                                if ev.get("professor"):
                                    notice += f"\n- 담당: {ev.get('professor')} 교수님"
                                if ev.get("memo"):
                                    notice += f"\n- 내용: {ev.get('memo')}"
                                st.session_state.active_notice_text = notice
                                st.rerun()

st.divider()

# ==============================================================================
# ----------------- 구글 캘린더 스타일 월간 그리드 -----------------
# ==============================================================================

gcal_nav1, gcal_nav2, gcal_nav3, gcal_nav4 = st.columns([1.2, 0.6, 0.6, 6])

with gcal_nav1:
    if st.button("오늘", use_container_width=True):
        st.session_state.current_year = today.year
        st.session_state.current_month = today.month
        st.session_state.selected_date = today
        st.rerun()

with gcal_nav2:
    if st.button("◀", use_container_width=True):
        if st.session_state.current_month == 1:
            st.session_state.current_month = 12
            st.session_state.current_year -= 1
        else:
            st.session_state.current_month -= 1
        st.rerun()

with gcal_nav3:
    if st.button("▶", use_container_width=True):
        if st.session_state.current_month == 12:
            st.session_state.current_month = 1
            st.session_state.current_year += 1
        else:
            st.session_state.current_month += 1
        st.rerun()

with gcal_nav4:
    st.markdown(
        f"<h3 style='margin: 0; padding-top: 4px; font-weight: 500; color: #3c4043; font-family: Roboto, -apple-system, sans-serif;'>"
        f"{st.session_state.current_year}년 {st.session_state.current_month}월"
        f"</h3>",
        unsafe_allow_html=True
    )

st.markdown("""
<style>
    .gcal-chip {
        font-size: 0.72rem;
        font-weight: 500;
        padding: 2px 6px;
        margin-bottom: 3px;
        border-radius: 4px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        display: block;
        line-height: 1.35;
    }
    .gcal-chip-red { background-color: #fce8e6; color: #c5221f; border-left: 3px solid #d93025; }
    .gcal-chip-violet { background-color: #f3e8fd; color: #8430ce; border-left: 3px solid #9334e6; }
    .gcal-chip-orange { background-color: #feefe3; color: #c26401; border-left: 3px solid #e8710a; }
    .gcal-chip-green { background-color: #e6f4ea; color: #137333; border-left: 3px solid #1e8e3e; }
    .gcal-chip-blue { background-color: #e8f0fe; color: #1967d2; border-left: 3px solid #1a73e8; }
    .gcal-chip-teal { background-color: #e4f7fb; color: #007b83; border-left: 3px solid #12b5cb; }
</style>
""", unsafe_allow_html=True)

cal_matrix = calendar.monthcalendar(st.session_state.current_year, st.session_state.current_month)
weekday_headers = ["월", "화", "수", "목", "금", "토", "일"]

header_cols = st.columns(7)
for idx, day_str in enumerate(weekday_headers):
    color = "#d93025" if idx == 6 else ("#1a73e8" if idx == 5 else "#70757a")
    header_cols[idx].markdown(
        f"<div style='text-align: center; font-size: 0.8rem; font-weight: 600; color: {color}; padding: 6px 0; border-bottom: 1px solid #dadce0;'>"
        f"{day_str}"
        f"</div>",
        unsafe_allow_html=True
    )

def get_chip_class(ev_type):
    if ev_type == "보강" or ev_type == "시험":
        return "gcal-chip-red"
    elif ev_type == "휴강":
        return "gcal-chip-violet"
    elif ev_type == "강의실변경":
        return "gcal-chip-orange"
    elif ev_type == "과제":
        return "gcal-chip-green"
    elif ev_type == "기타":
        return "gcal-chip-teal"
    return "gcal-chip-blue"

# 캘린더 그리드 렌더링
for week in cal_matrix:
    cols = st.columns(7)
    for i, day_num in enumerate(week):
        with cols[i]:
            if day_num == 0:
                st.markdown("<div style='min-height: 110px; background-color: #f8f9fa; border: 1px solid #f1f3f4; border-radius: 6px; margin-bottom: 6px;'></div>", unsafe_allow_html=True)
            else:
                cell_date = date(st.session_state.current_year, st.session_state.current_month, day_num)
                date_str = cell_date.strftime("%Y-%m-%d")

                day_events = []
                for s in all_schedules:
                    try:
                        s_dt = datetime.strptime(s["date"], "%Y-%m-%d").date()
                        e_dt = datetime.strptime(s.get("end_date", s["date"]), "%Y-%m-%d").date()
                        if s_dt <= cell_date <= e_dt:
                            day_events.append(s)
                    except Exception:
                        continue

                is_selected = (cell_date == st.session_state.selected_date)
                is_today = (cell_date == today)

                btn_type = "primary" if is_selected else "secondary"
                btn_title = f"{day_num}일"
                if is_today:
                    btn_title = f"🔵 {day_num}일 (오늘)"
                elif is_selected:
                    btn_title = f"✓ {day_num}일"

                if st.button(btn_title, key=f"date_btn_{date_str}", type=btn_type, use_container_width=True):
                    st.session_state.selected_date = cell_date
                    st.session_state.editing_schedule_id = None
                    st.rerun()

                chips_html = ""
                for ev in day_events[:3]:
                    ev_type = ev.get("type", "일정")
                    c_class = get_chip_class(ev_type)
                    if ev.get("is_range", False):
                        time_label = "기간"
                    else:
                        sp = ev.get("start_period", 1)
                        ep = ev.get("end_period", sp)
                        time_label = f"{sp}~{ep}교시" if sp != ep else f"{sp}교시"
                    chips_html += f"<div class='gcal-chip {c_class}'><strong>[{ev_type}]</strong> {ev.get('title')} ({time_label})</div>"

                if len(day_events) > 3:
                    chips_html += f"<div style='font-size: 0.68rem; color: #70757a; font-weight: 500; padding-left: 2px;'>+ {len(day_events)-3}개 더보기</div>"

                if not day_events:
                    chips_html = "<div style='min-height: 48px;'></div>"

                st.markdown(f"<div style='margin-top: -8px; margin-bottom: 8px;'>{chips_html}</div>", unsafe_allow_html=True)

st.divider()

# ----------------- 하단 상세 및 일정 추가/수정 -----------------
selected_str = st.session_state.selected_date.strftime("%Y-%m-%d")
sel_w_name = weekday_headers[st.session_state.selected_date.weekday()]

st.subheader(f"📌 {selected_str} ({sel_w_name}요일) 일정 관리")

day_regular_classes = TIMETABLE_2026_2.get(sel_w_name, [])
if day_regular_classes:
    st.markdown(f"**⚡ {sel_w_name}요일 정규 수업 (누르면 폼에 자동 입력):**")
    tag_cols = st.columns(len(day_regular_classes) + 1)
    for idx, c in enumerate(day_regular_classes):
        with tag_cols[idx]:
            btn_label = f"📌 {c['name']} ({c['start']}~{c['end']}교시)"
            if st.button(btn_label, key=f"quick_fill_{idx}", use_container_width=True):
                st.session_state.inp_title = c["name"]
                st.session_state.form_start_period = c["start"]
                st.session_state.form_end_period = c["end"]
                st.rerun()

col_detail, col_add_or_edit = st.columns([3, 2])

# 좌측: 해당 일자 일정 목록 (브라우저 공식 원클릭 복사 지원)
with col_detail:
    st.markdown("#### 등록된 일정")
    target_events = []
    for s in all_schedules:
        try:
            s_dt = datetime.strptime(s["date"], "%Y-%m-%d").date()
            e_dt = datetime.strptime(s.get("end_date", s["date"]), "%Y-%m-%d").date()
            if s_dt <= st.session_state.selected_date <= e_dt:
                target_events.append(s)
        except Exception:
            continue

    if not target_events:
        st.info("해당 일자에 등록된 특별 일정이 없습니다.")
    else:
        for item in target_events:
            with st.container(border=True):
                c_info, c_actions = st.columns([7, 3])
                ev_type = item.get("type", "일정")
                is_range = item.get("is_range", False)

                type_colors = {
                    "보강": "red", "휴강": "violet", "시험": "red",
                    "과제": "green", "강의실변경": "orange", "정규강의": "blue", "기타": "teal"
                }
                badge_color = type_colors.get(ev_type, "gray")

                with c_info:
                    st.markdown(f"### :{badge_color}[[{ev_type}]] **{item.get('title')}**")
                    if is_range:
                        st.write(f"📅 **기간:** {item.get('date')} ~ {item.get('end_date')} | 📍 **장소:** {item.get('room', '-')}")
                    else:
                        sp = item.get("start_period", 1)
                        ep = item.get("end_period", sp)
                        period_display = f"{sp}~{ep}교시" if sp != ep else f"{sp}교시"
                        start_clock = PERIOD_TIMES.get(sp, ("09:00", "09:50"))[0]
                        end_clock = PERIOD_TIMES.get(ep, ("17:00", "17:50"))[1]
                        st.write(f"🕒 **시간:** {period_display} ({start_clock} ~ {end_clock}) | 📍 **장소:** {item.get('room', '-')}")
                        if item.get("professor"):
                            st.caption(f"교수: {item.get('professor')} 교수님")
                    if item.get("memo"):
                        st.caption(f"비고: {item.get('memo')}")

                with c_actions:
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button("✏️ 수정", key=f"edit_btn_{item.get('id')}", use_container_width=True):
                            st.session_state.editing_schedule_id = item.get("id")
                            st.rerun()
                    with btn_col2:
                        if st.button("🗑️ 삭제", key=f"del_ev_{item.get('id')}", use_container_width=True):
                            st.session_state.app_data["schedules"] = [x for x in all_schedules if x.get("id") != item.get("id")]
                            if st.session_state.editing_schedule_id == item.get("id"):
                                st.session_state.editing_schedule_id = None
                            save_data(st.session_state.app_data)
                            st.rerun()

                # 공지 텍스트 조립
                if is_range:
                    notice_lines = [
                        f"📢 [{item.get('type')}] {item.get('title')}",
                        f"- 기간: {item.get('date')} ~ {item.get('end_date')}",
                        f"- 장소: {item.get('room', '-')}",
                    ]
                else:
                    sp = item.get("start_period", 1)
                    ep = item.get("end_period", sp)
                    period_display = f"{sp}~{ep}교시" if sp != ep else f"{sp}교시"
                    start_clock = PERIOD_TIMES.get(sp, ("09:00", "09:50"))[0]
                    end_clock = PERIOD_TIMES.get(ep, ("17:00", "17:50"))[1]
                    notice_lines = [
                        f"📢 [{item.get('type')}] {item.get('title')}",
                        f"- 일시: {selected_str} {period_display} ({start_clock}~{end_clock})",
                        f"- 장소: {item.get('room', '-')}",
                    ]
                if item.get("professor"):
                    notice_lines.append(f"- 담당: {item.get('professor')} 교수님")
                if item.get("memo"):
                    notice_lines.append(f"- 내용: {item.get('memo')}")
                notice_text = "\n".join(notice_lines)

                # 브라우저 보안 제약 없는 Streamlit 공식 원클릭 복사 코드 블록
                st.caption("📋 아래 박스 오른쪽 위의 복사 버튼을 누르면 단톡에 바로 붙여넣을 수 있습니다:")
                st.code(notice_text, language="text")

# 우측: 일정 등록 및 수정
with col_add_or_edit:
    if st.session_state.editing_schedule_id is not None:
        target_sched = next((s for s in all_schedules if s.get("id") == st.session_state.editing_schedule_id), None)
        if not target_sched:
            st.session_state.editing_schedule_id = None
            st.rerun()

        st.markdown(f"#### ✏️ 일정 수정 (ID: #{target_sched.get('id')})")
        with st.container(border=True):
            type_options = ["보강", "휴강", "시험", "과제", "강의실변경", "정규강의", "기타"]
            cur_type = target_sched.get("type", "보강")
            type_idx = type_options.index(cur_type) if cur_type in type_options else 0
            
            edit_type = st.selectbox("구분", type_options, index=type_idx, key="edit_type")
            edit_title = st.text_input("일정명 / 과목명", value=target_sched.get("title", ""), key="edit_title")

            if edit_type == "기타":
                cur_s_dt = datetime.strptime(target_sched.get("date", selected_str), "%Y-%m-%d").date()
                cur_e_dt = datetime.strptime(target_sched.get("end_date", target_sched.get("date", selected_str)), "%Y-%m-%d").date()
                edit_range = st.date_input("기간 선택 (시작일 ~ 종료일)", value=(cur_s_dt, cur_e_dt), key="edit_range_date")
                edit_room = st.text_input("장소", value=target_sched.get("room", ""), key="edit_room_other")
                edit_prof = ""
            else:
                edit_prof = st.text_input("담당 교수명", value=target_sched.get("professor", ""), key="edit_prof")
                
                if "edit_start_period" not in st.session_state:
                    st.session_state.edit_start_period = target_sched.get("start_period", 1)
                if "edit_end_period" not in st.session_state:
                    st.session_state.edit_end_period = target_sched.get("end_period", target_sched.get("start_period", 1))

                cp1, cp2 = st.columns(2)
                with cp1:
                    st.selectbox(
                        "시작 교시",
                        options=list(PERIOD_TIMES.keys()),
                        key="edit_start_period",
                        format_func=lambda x: f"{x}교시 ({PERIOD_TIMES[x][0]})",
                        on_change=on_edit_start_period_change
                    )
                with cp2:
                    allowed_end = [p for p in PERIOD_TIMES.keys() if p >= st.session_state.edit_start_period]
                    if st.session_state.edit_end_period not in allowed_end:
                        st.session_state.edit_end_period = allowed_end[0]
                    st.selectbox(
                        "끝 교시",
                        options=allowed_end,
                        key="edit_end_period",
                        format_func=lambda x: f"{x}교시 ({PERIOD_TIMES[x][1]})"
                    )

                orig_room = target_sched.get("room", "A3관 202호")
                bldg_val = "A3관"
                room_val = "202호"
                if "A2관" in orig_room:
                    bldg_val = "A2관"
                    room_val = orig_room.replace("A2관", "").strip()
                elif "A3관" in orig_room:
                    bldg_val = "A3관"
                    room_val = orig_room.replace("A3관", "").strip()

                c_b, c_r = st.columns([1, 1])
                with c_b:
                    bldg_idx = 0 if bldg_val == "A3관" else 1
                    edit_bldg = st.selectbox("건물", ["A3관", "A2관"], index=bldg_idx, key="edit_bldg")
                with c_r:
                    edit_room_detail = st.text_input("호실", value=room_val if room_val else "202호", key="edit_room_detail")
                edit_room = f"{edit_bldg} {edit_room_detail}".strip()

            edit_memo = st.text_area("특이사항 / 준비물 / 사유", value=target_sched.get("memo", ""), height=75, key="edit_memo")

            btn_save, btn_cancel = st.columns(2)
            with btn_save:
                if st.button("수정 완료", type="primary", use_container_width=True):
                    if not edit_title:
                        st.error("일정명을 입력해주세요.")
                    else:
                        target_sched["title"] = edit_title
                        target_sched["type"] = edit_type
                        target_sched["memo"] = edit_memo
                        target_sched["room"] = edit_room

                        if edit_type == "기타":
                            if isinstance(edit_range, (tuple, list)) and len(edit_range) == 2:
                                s_d, e_d = edit_range
                            elif isinstance(edit_range, (tuple, list)) and len(edit_range) == 1:
                                s_d = e_d = edit_range[0]
                            else:
                                s_d = e_d = edit_range
                            target_sched["date"] = s_d.strftime("%Y-%m-%d")
                            target_sched["end_date"] = e_d.strftime("%Y-%m-%d")
                            target_sched["is_range"] = True
                            target_sched["professor"] = ""
                        else:
                            target_sched["professor"] = edit_prof
                            target_sched["is_range"] = False
                            target_sched["start_period"] = st.session_state.edit_start_period
                            target_sched["end_period"] = st.session_state.edit_end_period

                        save_data(st.session_state.app_data)
                        st.session_state.editing_schedule_id = None
                        st.success("일정이 성공적으로 수정되었습니다.")
                        st.rerun()

            with btn_cancel:
                if st.button("수정 취소", use_container_width=True):
                    st.session_state.editing_schedule_id = None
                    st.rerun()

    else:
        st.markdown(f"#### `{selected_str}` 새 일정 추가")
        with st.container(border=True):
            course_options = ["직접 입력"]
            for d in ["월", "화", "수", "목", "금"]:
                for c in TIMETABLE_2026_2[d]:
                    course_options.append(f"[{d}] {c['name']} ({c['start']}~{c['end']}교시)")

            def on_quick_select():
                sel = st.session_state.quick_course_choice
                if sel != "직접 입력":
                    course_title = sel.split("] ")[1].split(" (")[0]
                    period_part = sel.split("(")[1].replace("교시)", "")
                    if "~" in period_part:
                        sp, ep = map(int, period_part.split("~"))
                    else:
                        sp = ep = int(period_part)
                    st.session_state.inp_title = course_title
                    st.session_state.form_start_period = sp
                    st.session_state.form_end_period = ep

            st.selectbox(
                "⚡ 2026-2 시간표에서 과목 불러오기",
                options=course_options,
                key="quick_course_choice",
                on_change=on_quick_select
            )

            f_type = st.selectbox(
                "구분",
                ["보강", "휴강", "시험", "과제", "강의실변경", "정규강의", "기타"],
                key="inp_type"
            )
            f_title = st.text_input("일정명 / 과목명", key="inp_title")
            
            if f_type == "기타":
                range_dates = st.date_input(
                    "기간 선택 (시작일 ~ 종료일)",
                    value=(st.session_state.selected_date, st.session_state.selected_date + timedelta(days=2)),
                    key="inp_range_date"
                )
                f_room = st.text_input("장소", placeholder="예: 대강당, 운동장, 학생회관", key="inp_room_other")
                f_prof = ""
            else:
                f_prof = st.text_input("담당 교수명", placeholder="교수님 성함", key="inp_prof")
                c_p1, c_p2 = st.columns(2)
                with c_p1:
                    st.selectbox(
                        "시작 교시",
                        options=list(PERIOD_TIMES.keys()),
                        key="form_start_period",
                        format_func=lambda x: f"{x}교시 ({PERIOD_TIMES[x][0]})",
                        on_change=on_start_period_change
                    )
                with c_p2:
                    allowed_end_periods = [p for p in PERIOD_TIMES.keys() if p >= st.session_state.form_start_period]
                    if st.session_state.form_end_period not in allowed_end_periods:
                        st.session_state.form_end_period = allowed_end_periods[0]
                        
                    st.selectbox(
                        "끝 교시",
                        options=allowed_end_periods,
                        key="form_end_period",
                        format_func=lambda x: f"{x}교시 ({PERIOD_TIMES[x][1]})"
                    )

                c_bldg, c_room = st.columns([1, 1])
                with c_bldg:
                    bldg_choice = st.selectbox("건물", ["A3관", "A2관"], index=0, key="inp_bldg")
                with c_room:
                    room_choice = st.text_input("호실", value="202호", key="inp_room")
                f_room = f"{bldg_choice} {room_choice}".strip()

            f_memo = st.text_area("특이사항 / 준비물 / 사유", placeholder="세부 내용 입력", height=75, key="inp_memo")

            if st.button("일정 등록하기", type="primary", use_container_width=True):
                if not f_title:
                    st.error("일정명을 입력해주세요.")
                else:
                    new_id = max([s.get("id", 0) for s in st.session_state.app_data.get("schedules", [])], default=0) + 1
                    
                    if f_type == "기타":
                        if isinstance(range_dates, (tuple, list)) and len(range_dates) == 2:
                            s_d, e_d = range_dates
                        elif isinstance(range_dates, (tuple, list)) and len(range_dates) == 1:
                            s_d = e_d = range_dates[0]
                        else:
                            s_d = e_d = range_dates

                        new_entry = {
                            "id": new_id,
                            "title": f_title,
                            "type": "기타",
                            "professor": "",
                            "date": s_d.strftime("%Y-%m-%d"),
                            "end_date": e_d.strftime("%Y-%m-%d"),
                            "is_range": True,
                            "room": f_room if f_room else "-",
                            "memo": f_memo
                        }
                    else:
                        new_entry = {
                            "id": new_id,
                            "title": f_title,
                            "type": f_type,
                            "professor": f_prof,
                            "date": selected_str,
                            "end_date": selected_str,
                            "is_range": False,
                            "start_period": st.session_state.form_start_period,
                            "end_period": st.session_state.form_end_period,
                            "room": f_room,
                            "memo": f_memo
                        }

                    st.session_state.app_data.setdefault("schedules", []).append(new_entry)
                    save_data(st.session_state.app_data)
                    st.success("일정이 등록되었습니다.")
                    st.rerun()