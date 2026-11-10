import os
import platform
import re
import time
import urllib.request
from PIL import Image
import google.generativeai as genai
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

# -------------------------------------------------------------------
# [한글 폰트 자동 다운로드 & Matplotlib 등록 로직]
# -------------------------------------------------------------------
FONT_PATH = "NanumGothic.ttf"
if not os.path.exists(FONT_PATH):
    try:
        font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
        urllib.request.urlretrieve(font_url, FONT_PATH)
    except Exception:
        pass

if os.path.exists(FONT_PATH):
    fm.fontManager.addfont(FONT_PATH)
    font_prop = fm.FontProperties(fname=FONT_PATH)
    plt.rc("font", family=font_prop.get_name())

plt.rcParams["axes.unicode_minus"] = False

# -------------------------------------------------------------------
# 1. 페이지 기본 설정 및 커스텀 CSS
# -------------------------------------------------------------------
st.set_page_config(
    page_title="AI 미적분 헬퍼 (Light Edition)",
    page_icon="📐",
    layout="wide"
)

st.markdown(
    """
<style>
    /* 전체 앱 배경 및 기본 글자색 (화이트 테마) */
    .stApp {
        background-color: #ffffff;
        color: #0f172a;
    }
    header, footer {
        background-color: #ffffff !important;
    }
    
    h1, h2, h3, h4, h5, h6, p, label, span {
        color: #0f172a !important;
    }

    /* 사이드바 */
    section[data-testid="stSidebar"] {
        background-color: #f8fafc !important;
        border-right: 1px solid #e2e8f0;
    }

    div[data-testid="stSidebar"] div[data-testid="stAlert"] {
        background-color: #e0f2fe !important;
        border: 1px solid #0284c7 !important;
        border-radius: 8px !important;
    }
    div[data-testid="stSidebar"] div[data-testid="stAlert"] * {
        color: #0369a1 !important;
        font-weight: 600 !important;
    }

    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"] {
        background-color: #ffffff !important;
    }
    li[role="option"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
    }
    li[role="option"]:hover, li[role="option"][aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
    }
    input[type="text"], input[type="password"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
    }

    /* 파일 업로드 구역 */
    section[data-testid="stFileUploadDropzone"] {
        background-color: #f8fafc !important;
        border: 2px dashed #0284c7 !important;
        border-radius: 12px !important;
        padding: 20px !important;
    }
    section[data-testid="stFileUploadDropzone"] * {
        color: #0f172a !important;
        font-weight: 600 !important;
    }
    section[data-testid="stFileUploadDropzone"] button {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: bold !important;
    }
    section[data-testid="stFileUploadDropzone"] button * {
        color: #ffffff !important;
    }

    div[data-testid="stRadio"] > div {
        background-color: #f8fafc;
        padding: 10px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
    }

    .stButton>button {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
        color: #ffffff !important;
        border: none;
        border-radius: 8px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background: #0369a1;
        color: #ffffff !important;
    }

    /* 우측 하단 소형 미니 채팅 버튼 (40px) */
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
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
        color: #ffffff !important;
        font-size: 16px !important;
        box-shadow: 0px 4px 12px rgba(2, 132, 199, 0.3) !important;
        border: none !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    div[data-testid="stPopoverBody"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 12px !important;
        color: #0f172a !important;
        width: 340px !important;
        max-width: 85vw !important;
        box-shadow: 0px 10px 25px rgba(0, 0, 0, 0.1) !important;
    }
    div[data-testid="stPopoverBody"] h1,
    div[data-testid="stPopoverBody"] h2,
    div[data-testid="stPopoverBody"] h3,
    div[data-testid="stPopoverBody"] h4,
    div[data-testid="stPopoverBody"] p,
    div[data-testid="stPopoverBody"] span {
        color: #0f172a !important;
    }

    div[data-testid="stChatMessage"] {
        background-color: #f1f5f9 !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        padding: 10px 12px !important;
        margin-bottom: 8px !important;
    }
    div[data-testid="stChatMessage"] * {
        color: #0f172a !important;
        font-weight: 500 !important;
    }

    div[data-testid="stChatInput"] textarea,
    div[data-testid="stChatInput"] input {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 2px solid #0284c7 !important;
        font-weight: bold !important;
    }
    div[data-testid="stChatInput"] textarea::placeholder,
    div[data-testid="stChatInput"] input::placeholder {
        color: #64748b !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title("📐 AI 미적분 풀이 & 시각화 헬퍼")
st.caption("사진을 업로드하면 AI가 단계별 풀이와 함께 한국어로 표시된 맞춤형 그래프를 생성합니다.")

# -------------------------------------------------------------------
# 세션 상태(Session State)
# -------------------------------------------------------------------
if "api_key" not in st.session_state:
    st.session_state["api_key"] = ""
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "last_explanation" not in st.session_state:
    st.session_state["last_explanation"] = ""
if "generated_python_code" not in st.session_state:
    st.session_state["generated_python_code"] = ""

# -------------------------------------------------------------------
# 사이드바: API 키 및 모델 선택
# -------------------------------------------------------------------
st.sidebar.header("🔑 API 및 모델 설정")

api_key_input = st.sidebar.text_input(
    "Google Gemini API Key",
    value=st.session_state["api_key"],
    type="password",
    help="Google AI Studio에서 발급받은 키를 입력하세요.",
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
                if "gemini" in name and not any(
                    x in name for x in ["embedding", "bison", "imagen"]
                ):
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
input_method = st.radio(
    "사진 입력 방식", ["파일 업로드", "카메라 직접 촬영"], horizontal=True
)

uploaded_image = None
if input_method == "파일 업로드":
    uploaded_file = st.file_uploader(
        "미적분 문제 이미지 선택 (JPG, PNG)", type=["jpg", "jpeg", "png"]
    )
    if uploaded_file:
        uploaded_image = Image.open(uploaded_file)
else:
    camera_file = st.camera_input("문제 사진 촬영")
    if camera_file:
        uploaded_image = Image.open(camera_file)

# -------------------------------------------------------------------
# 풀이 및 시각화 생성 로직
# -------------------------------------------------------------------
if uploaded_image:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🖼️ 업로드된 문제")
        st.image(uploaded_image, use_container_width=True)

    with col2:
        st.subheader("🚀 문제 분석 및 그래프 생성")
        st.write(f"가동 모델: **`{selected_model}`**")
        solve_button = st.button(
            "✨ AI 풀이 & 그래프 시각화", type="primary", use_container_width=True
        )

    if solve_button:
        active_api_key = st.session_state.get("api_key", "").strip()

        if not active_api_key:
            st.error("⚠️ 사이드바에 API Key를 먼저 입력해 주세요!")
        else:
            with st.spinner(f"[{selected_model}] 모델이 분석 중입니다..."):
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
                   - import matplotlib.pyplot as plt 및 import numpy as np 포함
                   - 모든 축, 라벨, 범례, 텍스트 설명은 반드시 '한국어'로 작성해줘 (예: '함수 f(x)', '접선 y=x', '정적분 영역 S', '극댓값').
                   - 문제 해결에 필요한 주요 핵심 점(극점, 변곡점, 절편, 접점 등)을 plt.scatter()와 plt.annotate()로 표시해줘.
                   - 라이트 테마 색상 가이드:
                     * plt.style.use('default') 적용
                     * 배경: 깔끔한 흰색 (#ffffff)
                     * 주 함수 f(x): 선명한 파란색 ('#0284c7', lw=2.5)
                     * 도함수/접선: 붉은색 ('#e11d48', lw=2)
                     * 핵심 좌표점: 주황/녹색 ('#d97706', '#059669', s=60)
                     * 모든 축 및 눈금, 글자: 짙은 네이비/검은색 ('#0f172a')
                     * plt.grid(True, color='#e2e8f0', alpha=0.7)
                   - 맨 마지막에 plt.show()를 작성하지 마.
                """

                response_text = None
                trials = [selected_model] + [
                    m for m in valid_models if m != selected_model
                ]

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
                    code_match = re.search(
                        r"```python(.*?)```", response_text, re.DOTALL
                    )
                    clean_explanation = re.sub(
                        r"```python.*?```", "", response_text, flags=re.DOTALL
                    ).strip()

                    st.session_state["last_explanation"] = clean_explanation
                    if code_match:
                        st.session_state["generated_python_code"] = (
                            code_match.group(1).strip()
                        )
                    else:
                        st.session_state["generated_python_code"] = ""
                else:
                    st.error(
                        "🚨 선택한 API 키의 요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
                    )

# -------------------------------------------------------------------
# 해설 출력 & 한글 폰트 적용 그래프 렌더링
# -------------------------------------------------------------------
if st.session_state["last_explanation"]:
    st.divider()
    st.subheader("📖 AI 미적분 상세 해설")
    st.markdown(st.session_state["last_explanation"])

    st.divider()
    st.subheader("📈 미적분 함수 & 핵심 요소 시각화")

    python_code = st.session_state.get("generated_python_code", "")

    if python_code:
        try:
            plt.close("all")
            plt.style.use("default")

            if os.path.exists(FONT_PATH):
                font_prop = fm.FontProperties(fname=FONT_PATH)
                plt.rc("font", family=font_prop.get_name())

            plt.rcParams["axes.unicode_minus"] = False

            local_scope = {"np": np, "plt": plt}
            exec(python_code, local_scope)

            fig = plt.gcf()
            fig.patch.set_facecolor("#ffffff")

            for ax in fig.get_axes():
                ax.set_facecolor("#ffffff")
                ax.tick_params(colors="#0f172a", labelsize=10)
                ax.xaxis.label.set_color("#0f172a")
                ax.yaxis.label.set_color("#0f172a")
                ax.title.set_color("#0f172a")
                for spine in ax.spines.values():
                    spine.set_color("#cbd5e1")

            st.pyplot(fig, use_container_width=True)
            plt.close("all")

        except Exception as plot_err:
            st.warning("그래프 시각화 처리 중 오류가 발생했습니다.")
    else:
        st.info("이 문제에는 시각화 코드가 생략되었거나 수식 전용 문제입니다.")

# -------------------------------------------------------------------
# [우측 하단 구석 40px 미니 버튼] 실시간 스트리밍 1:1 꼬리질문 AI 튜터
# -------------------------------------------------------------------
with st.popover("💬", help="1:1 AI 튜터 꼬리질문"):
    st.markdown("#### 💬 AI 튜터 1:1 질의응답")
    st.caption("해설 중 이해가 안 가는 수식을 질문해 보세요.")

    chat_container = st.container(height=300)
    with chat_container:
        if not st.session_state["chat_history"]:
            st.info("👋 궁금한 점을 질문하시면 실시간으로 친절히 설명해 드립니다!")
        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    user_query = st.chat_input("질문을 입력하세요...")
    if user_query:
        # 1. 사용자 질문을 세션 상태에 즉시 저장
        st.session_state["chat_history"].append(
            {"role": "user", "content": user_query}
        )

        active_api_key = st.session_state.get("api_key", "").strip()
        if not active_api_key:
            error_msg = "⚠️ 사이드바에 API Key를 먼저 입력해 주세요!"
            st.session_state["chat_history"].append(
                {"role": "assistant", "content": error_msg}
            )
            st.rerun()
        else:
            # 2. 질문 입력 즉시 사용자 메시지와 답변 스트리밍을 화면에 실시간 출력
            with chat_container:
                with st.chat_message("user"):
                    st.write(user_query)

                with st.chat_message("assistant"):
                    try:
                        genai.configure(api_key=active_api_key)
                        tutor_model = genai.GenerativeModel(
                            selected_model or "gemini-2.0-flash"
                        )

                        explanation_context = st.session_state.get(
                            "last_explanation", "아직 해설된 문제 없음"
                        )

                        tutor_prompt = f"""
                        너는 친절한 고등학교 미적분 AI 튜터야.
                        학생이 방금 해설을 읽고 다음과 같이 질문했어. 학생 눈높이에 맞춰 친절하게 설명해줘.

                        [문제 해설 맥락]
                        {explanation_context}

                        [학생 질문]
                        {user_query}
                        """

                        # Gemini 실시간 토큰 스트리밍 함수
                        def generate_stream():
                            response = tutor_model.generate_content(
                                tutor_prompt, stream=True
                            )
                            for chunk in response:
                                if chunk.text:
                                    yield chunk.text

                        # st.write_stream을 사용하여 즉각적으로 타자 치듯 화면 출력
                        full_response = st.write_stream(generate_stream())
                        
                        # 완성된 답변을 채팅 내역 세션에 기록
                        st.session_state["chat_history"].append(
                            {"role": "assistant", "content": full_response}
                        )
                    except Exception as e:
                        err_msg = f"답변 생성 오류: {e}"
                        st.write(err_msg)
                        st.session_state["chat_history"].append(
                            {"role": "assistant", "content": err_msg}
                        )

            st.rerun()
