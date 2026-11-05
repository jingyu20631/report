import re
import time
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import google.generativeai as genai
import streamlit as st

# 1. 페이지 설정
st.set_page_config(
    page_title="AI 미적분 헬퍼 (Dark Edition)",
    page_icon="📐",
    layout="wide"
)

# 2. 다크 테마 커스텀 CSS (시인성 최우선 반영)
st.markdown("""
<style>
    /* 전체 배경 */
    .stApp {
        background-color: #0b0f19;
        color: #f8fafc;
    }
    header, footer {
        background-color: #0b0f19 !important;
    }
    
    /* 기본 글자색 고정 */
    h1, h2, h3, h4, h5, h6, p, label, span {
        color: #f8fafc !important;
    }

    /* 사이드바 */
    section[data-testid="stSidebar"] {
        background-color: #111827 !important;
        border-right: 1px solid #1e293b;
    }

    /* Selectbox 및 입력창 */
    div[data-baseweb="select"] > div {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 1px solid #38bdf8 !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"] {
        background-color: #1e293b !important;
    }
    li[role="option"] {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }
    li[role="option"]:hover, li[role="option"][aria-selected="true"] {
        background-color: #38bdf8 !important;
        color: #0f172a !important;
    }
    input[type="text"], input[type="password"] {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
    }

    /* 파일 업로드 구역 대비 강조 */
    section[data-testid="stFileUploadDropzone"] {
        background-color: #1e2238 !important;
        border: 2px dashed #38bdf8 !important;
        border-radius: 12px !important;
        padding: 20px !important;
    }
    section[data-testid="stFileUploadDropzone"] * {
        color: #f8fafc !important;
    }
    section[data-testid="stFileUploadDropzone"] button {
        background-color: #0f172a !important;
        color: #38bdf8 !important;
        border: 1px solid #38bdf8 !important;
        border-radius: 6px !important;
    }

    /* 라디오 버튼 박스 */
    div[data-testid="stRadio"] > div {
        background-color: #1e2238;
        padding: 10px;
        border-radius: 10px;
        border: 1px solid #334155;
    }

    /* -----------------------------------------------------------
       우측 하단 구석 미니 채팅 버튼 (40px) & 공간 차단 레이아웃
       ----------------------------------------------------------- */
    div[data-testid="stElementContainer"]:has(div[data-testid="stPopover"]) {
        position: fixed !important;
        bottom: 20px !important;
        right: 20px !important;
        width: 0px !important;
        height: 0px !important;
        margin: 0 !important;
        padding: 0 !important;
        z-index: 999999 !important;
    }

    div[data-testid="stPopover"] {
        position: fixed !important;
        bottom: 20px !important;
        right: 20px !important;
        width: auto !important;
        height: auto !important;
        z-index: 999999 !important;
    }

    div[data-testid="stPopover"] > button {
        width: 40px !important;
        height: 40px !important;
        min-width: 40px !important;
        min-height: 40px !important;
        max-width: 40px !important;
        max-height: 40px !important;
        border-radius: 50% !important;
        background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%) !important;
        color: #0f172a !important;
        font-size: 16px !important;
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.5) !important;
        border: none !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    div[data-testid="stPopoverBody"] {
        background-color: #111827 !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        color: #f8fafc !important;
        width: 320px !important;
        max-width: 85vw !important;
    }
    div[data-testid="stChatMessage"] {
        background-color: #1e293b !important;
        border-radius: 8px !important;
        padding: 8px 10px !important;
        margin-bottom: 6px !important;
    }
    div[data-testid="stChatMessage"] * {
        color: #f8fafc !important;
    }
    div[data-testid="stChatInput"] input {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 1px solid #38bdf8 !important;
    }

    /* 버튼 스타일 */
    .stButton>button {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        color: #38bdf8 !important;
        border: 1px solid #38bdf8;
        border-radius: 8px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background: #38bdf8;
        color: #0f172a !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("📐 AI 미적분 풀이 & 시각화 헬퍼")
st.caption("사진을 업로드하면 AI가 단계별 풀이와 선명한 미적분 시각화 그래프를 제공합니다.")

# -------------------------------------------------------------------
# 세션 상태(Session State)
# -------------------------------------------------------------------
if "api_key" not in st.session_state:
    st.session_state["api_key"] = ""
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "last_explanation" not in st.session_state:
    st.session_state["last_explanation"] = ""

# -------------------------------------------------------------------
# 사이드바: API 키 및 모델 설정
# -------------------------------------------------------------------
st.sidebar.header("🔑 API 및 모델 설정")

api_key_input = st.sidebar.text_input(
    "Google Gemini API Key",
    value=st.session_state["api_key"],
    type="password",
    help="Google AI Studio에서 발급받은 키를 입력하세요."
)

if api_key_input:
    st.session_state["api_key"] = api_key_input.strip()

valid_models = []
if st.session_state["api_key"]:
    try:
        genai.configure(api_key=st.session_state["api_key"])
        raw_models = []
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                name = m.name.replace("models/", "")
                if "gemini" in name and not any(x in name for x in ["embedding", "bison", "imagen"]):
                    raw_models.append(name)

        flash_models = [m for m in raw_models if "flash" in m.lower()]
        other_models = [m for m in raw_models if "flash" not in m.lower()]
        valid_models = flash_models + other_models

        if valid_models:
            st.sidebar.success(f"✅ 모델 {len(valid_models)}개 연결됨")
    except Exception as e:
        st.sidebar.error(f"API 연결 에러: {e}")

if valid_models:
    selected_model = st.sidebar.selectbox("사용할 AI 모델", valid_models, index=0)
else:
    selected_model = "gemini-2.0-flash"
    st.sidebar.info("💡 API 키를 입력하면 목록이 표시됩니다.")

# -------------------------------------------------------------------
# 메인 화면: 문제 업로드 영역
# -------------------------------------------------------------------
input_method = st.radio("사진 입력 방식", ["파일 업로드", "카메라 직접 촬영"], horizontal=True)

uploaded_image = None
if input_method == "파일 업로드":
    uploaded_file = st.file_uploader("미적분 문제 이미지 선택 (JPG, PNG)", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        uploaded_image = Image.open(uploaded_file)
else:
    camera_file = st.camera_input("문제 사진 촬영")
    if camera_file:
        uploaded_image = Image.open(camera_file)

# -------------------------------------------------------------------
# 풀이 및 시각화 로직
# -------------------------------------------------------------------
if uploaded_image:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🖼️ 업로드된 문제")
        st.image(uploaded_image, use_container_width=True)

    with col2:
        st.subheader("🚀 문제 분석 및 그래프 생성")
        st.write(f"가동 모델: **`{selected_model}`**")
        solve_button = st.button("✨ AI 풀이 & 그래프 시각화", type="primary", use_container_width=True)

    if solve_button:
        active_api_key = st.session_state.get("api_key", "").strip()

        if not active_api_key:
            st.error("⚠️ 사이드바에 API Key를 먼저 입력해 주세요!")
        else:
            with st.spinner(f"[{selected_model}] 모델이 분석을 진행 중입니다..."):
                genai.configure(api_key=active_api_key)

                prompt = """
                너는 최고의 미적분 수학 교사 및 시각화 전문가야.
                제공된 미적분 문제(도함수, 극값, 변곡점, 접선, 정적분 영역 등)를 분석해줘.

                [답변 양식]
                1. 📌 **문제 요약 및 핵심 조건**: 정리
                2. 💡 **출제 의도 및 필수 개념**: 핵심 공식 (LaTeX 표기)
                3. 📝 **단계별 상세 풀이**: Step 1, Step 2 순으로 설명
                4. ✅ **최종 정답**: 강조 표기

                5. 📊 **Matplotlib 그래프 작성 파이썬 코드를 맨 마지막에 작성해줘**:
                   - 코드 블록은 반드시 ```python 으로 시작하고 ``` 로 끝내야 해.
                   - 다크 배경에 잘 보이도록 색상 규칙을 반드시 지켜줘:
                     * plt.style.use('dark_background') 적용
                     * 배경은 어두운 색상(#111827 또는 #0b0f19)
                     * 주 함수 곡선 f(x) : 밝은 하늘색('#38bdf8') 및 두께 lw=2.5
                     * 접선 또는 도함수 : 밝은 핑크/레드('#f43f5e')
                     * 극점/변곡점/특이점 좌표 : 밝은 노란색('#f59e0b') 또는 연두색('#10b981') 점 및 텍스트
                     * 절대 검정색, 어두운 파란색 선/글자를 쓰지 마.
                     * 모든 축, 눈금, 라벨, 텍스트는 흰색('white')
                     * plt.grid(True, color='#334155', alpha=0.5)
                     * 맨 마지막에 plt.show()를 쓰지 말고 fig, ax 객체가 남아있도록 작성해줘.
                """

                response_text = None
                trials = [selected_model] + [m for m in valid_models if m != selected_model]

                for model_candidate in trials:
                    try:
                        model = genai.GenerativeModel(model_candidate)
                        response = model.generate_content([prompt, uploaded_image])
                        response_text = response.text
                        break
                    except Exception as err:
                        err_str = str(err)
                        if "429" in err_str or "Quota" in err_str:
                            time.sleep(1)
                            continue
                        elif "404" in err_str:
                            continue
                        else:
                            break

                if response_text:
                    # 파이썬 코드 추출 후 해설 텍스트에서 코드 블록 완벽 제거 (유저 화면에 코드 노출 안 됨)
                    code_match = re.search(r"```python(.*?)```", response_text, re.DOTALL)
                    clean_explanation = re.sub(r"```python.*?```", "", response_text, flags=re.DOTALL).strip()

                    st.session_state["last_explanation"] = clean_explanation

                    st.divider()
                    st.subheader("📖 AI 미적분 상세 해설")
                    st.markdown(clean_explanation)

                    st.divider()
                    st.subheader("📈 미적분 함수 & 핵심 단서 시각화")

                    if code_match:
                        python_code = code_match.group(1).strip()
                        
                        # 다크 모드 그래프 기본 세팅
                        plt.style.use('dark_background')
                        fig, ax = plt.subplots(figsize=(9, 5.5))
                        
                        fig.patch.set_facecolor('#111827')
                        ax.set_facecolor('#1e293b')
                        ax.tick_params(colors='white', labelsize=10)
                        for spine in ax.spines.values():
                            spine.set_color('#475569')

                        local_scope = {"np": np, "plt": plt, "fig": fig, "ax": ax}

                        try:
                            exec(python_code, local_scope)
                            st.pyplot(fig, use_container_width=True)
                            plt.close("all")
                        except Exception as plot_err:
                            st.warning("그래프 시각화 처리 중 문제가 발생하여 선명 모드로 재출력합니다.")
                            try:
                                st.pyplot(plt.gcf(), use_container_width=True)
                                plt.close("all")
                            except Exception:
                                st.info("그래프를 표현할 수 없는 수식 전용 문제입니다.")
                    else:
                        st.info("이 문제에는 시각화 코드가 생략되었거나 수식 전용 문제입니다.")
                else:
                    st.error("🚨 선택한 API 키의 요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요.")

# -------------------------------------------------------------------
# [우측 하단 구석 40px 미니 버튼] 1:1 꼬리질문 AI 튜터
# -------------------------------------------------------------------
with st.popover("💬", help="1:1 AI 튜터 꼬리질문"):
    st.markdown("#### 💬 AI 튜터 1:1 질의응답")
    st.caption("해설 중 이해가 안 가는 수식을 질문해 보세요.")

    chat_container = st.container(height=280)
    with chat_container:
        if not st.session_state["chat_history"]:
            st.info("👋 궁금한 점을 질문하시면 친절히 설명해 드립니다!")
        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    user_query = st.chat_input("질문을 입력하세요...")
    if user_query:
        st.session_state["chat_history"].append({"role": "user", "content": user_query})

        active_api_key = st.session_state.get("api_key", "").strip()
        if not active_api_key:
            st.session_state["chat_history"].append({"role": "assistant", "content": "⚠️ 사이드바에 API Key를 먼저 입력해 주세요!"})
        else:
            try:
                genai.configure(api_key=active_api_key)
                tutor_model = genai.GenerativeModel(selected_model or "gemini-2.0-flash")

                explanation_context = st.session_state.get("last_explanation", "아직 해설된 문제 없음")

                tutor_prompt = f"""
                너는 친절한 고등학교 미적분 AI 튜터야.
                학생이 방금 해설을 읽고 다음과 같이 질문했어. 학생 눈높이에 맞춰 친절하게 설명해줘.

                [문제 해설 맥락]
                {explanation_context}

                [학생 질문]
                {user_query}
                """

                res = tutor_model.generate_content(tutor_prompt)
                st.session_state["chat_history"].append({"role": "assistant", "content": res.text})
            except Exception as e:
                st.session_state["chat_history"].append({"role": "assistant", "content": f"답변 생성 오류: {e}"})

        st.rerun()
