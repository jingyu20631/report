import re
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
from PIL import Image
import google.generativeai as genai
import streamlit as st

# 1. 페이지 설정 및 다크(블랙) 테마 커스텀 CSS 적용
st.set_page_config(
    page_title="AI 미적분 헬퍼 (Dark Edition)",
    page_icon="📐",
    layout="wide"
)

st.markdown("""
<style>
    /* 전체 배경 블랙 & 글자 화이트 설정 */
    .stApp {
        background-color: #050505;
        color: #ffffff;
    }
    header, footer {
        background-color: #050505 !important;
    }
    p, h1, h2, h3, h4, h5, h6, label, div, span {
        color: #ffffff !important;
    }
    
    /* 사이드바 스타일링 */
    section[data-testid="stSidebar"] {
        background-color: #121212 !important;
        border-right: 1px solid #222222;
    }
    
    /* 버튼 스타일링 */
    .stButton>button {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        color: #38bdf8 !important;
        border: 1px solid #38bdf8;
        border-radius: 8px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background: #38bdf8;
        color: #000000 !important;
    }

    /* 우측 하단 고정 말풍선 (Floating Popover) 위치 설정 */
    div[data-testid="stPopover"] {
        position: fixed;
        bottom: 35px;
        right: 35px;
        z-index: 999999;
    }
    div[data-testid="stPopover"] > button {
        width: 60px;
        height: 60px;
        border-radius: 50% !important;
        background-color: #38bdf8 !important;
        color: #000000 !important;
        font-size: 24px;
        box-shadow: 0px 4px 15px rgba(56, 189, 248, 0.4);
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("📐 AI 미적분 풀이 & 인터랙티브 그래프 헬퍼")
st.caption("사진을 업로드하면 AI가 분석한 풀이와 함께 조작 가능한 인터랙티브 그래프를 제공합니다.")

# -------------------------------------------------------------------
# 세션 상태(Session State) 관리
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

# 사용 가능한 Gemini 모델 감지
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
    st.sidebar.info("💡 API 키를 입력하면 모델 목록이 동적으로 표시됩니다.")

# -------------------------------------------------------------------
# 메인 화면: 입력 영역
# -------------------------------------------------------------------
input_method = st.radio("사진 입력 방식", ["파일 업로드", "카메라 직접 촬영"], horizontal=True)

uploaded_image = None
if input_method == "파일 업로드":
    uploaded_file = st.file_uploader("미적분 문제 이미지 (JPG, PNG)", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        uploaded_image = Image.open(uploaded_file)
else:
    camera_file = st.camera_input("문제 사진 촬영")
    if camera_file:
        uploaded_image = Image.open(camera_file)

# -------------------------------------------------------------------
# 문제 풀이 및 시각화 로직
# -------------------------------------------------------------------
if uploaded_image:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🖼️ 업로드된 문제")
        st.image(uploaded_image, use_container_width=True)

    with col2:
        st.subheader("🚀 문제 분석 및 그래프 생성")
        st.write(f"가동 모델: **`{selected_model}`**")
        solve_button = st.button("✨ AI 풀이 & 인터랙티브 그래프 그리기", type="primary", use_container_width=True)

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

                5. 📊 **Matplotlib 그래프 작성 파이썬 코드를 포함해줘**:
                   - 함수 f(x), 도함수, 접선 또는 정적분 영역 시각화
                   - 파이썬 코드는 ```python 으로 시작하고 ``` 로 작성
                   - 극점, 변곡점, 정적분 구간은 plt.scatter()와 plt.annotate()로 정확히 표시
                   - 다크 테마 시각화를 위해 plt.style.use('dark_background') 적용
                   - 라벨/텍스트는 영문/수식(예: f(x), Local Max (2,4)) 사용
                   - 맨 마지막에 plt.show()를 호출하지 말고 fig 객체가 생성되도록 해줘.
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
                        if "429" in str(err) or "404" in str(err) or "Quota" in str(err):
                            continue
                        else:
                            break

                if response_text:
                    st.session_state["last_explanation"] = response_text
                    
                    st.divider()
                    st.subheader("📖 AI 미적분 상세 해설")
                    st.markdown(response_text)

                    st.divider()
                    st.subheader("📈 인터랙티브 그래프 탐색 (확대/축소 & 마우스 호버 지원)")

                    code_match = re.search(r"```python(.*?)```", response_text, re.DOTALL)

                    if code_match:
                        python_code = code_match.group(1).strip()
                        fig, ax = plt.subplots(figsize=(8, 5))
                        
                        # 다크 모드 그래프 스타일 설정
                        plt.style.use('dark_background')
                        fig.patch.set_facecolor('#050505')
                        ax.set_facecolor('#050505')

                        local_scope = {"np": np, "plt": plt, "fig": fig, "ax": ax}

                        try:
                            exec(python_code, local_scope)
                            
                            # Matplotlib Figure를 Plotly 인터랙티브 그래프로 변환하여 출력 (기능 3)
                            # 호버, 줌, 펜 탐색 기능 지원
                            plotly_fig = go.Figure(fig)
                            plotly_fig.update_layout(
                                template="plotly_dark",
                                paper_bgcolor="#050505",
                                plot_bgcolor="#050505",
                                margin=dict(l=20, r=20, t=30, b=20)
                            )
                            st.plotly_chart(plotly_fig, use_container_width=True)
                            plt.close("all")
                            
                        except Exception as plot_err:
                            # 실행 불가 시 기본 Matplotlib 렌더링
                            try:
                                st.pyplot(plt.gcf())
                                plt.close("all")
                            except Exception:
                                st.warning("그래프 생성 중 일부 요소 표현이 제한되었습니다.")
                    else:
                        st.info("이 문제에는 시각화 코드가 생략되었거나 수식 전용 문제입니다.")
                else:
                    st.error("🚨 사용 가능한 Gemini 모델의 요청 범위를 초과했습니다. 잠시 후 시도하거나 새 API 키를 입력해 주세요.")

# -------------------------------------------------------------------
# [기능 1] 우측 하단 플로팅 말풍선 버튼 -> 1:1 꼬리질문 AI 튜터 챗봇 Window
# -------------------------------------------------------------------
with st.popover("💬", help="AI 튜터에게 1:1 꼬리질문 하기"):
    st.markdown("### 💬 AI 튜터 1:1 질의응답")
    st.caption("해설 내용 중 이해가 안 되는 수식이나 개념을 자유롭게 질문하세요!")

    # 챗 히스토리 렌더링
    chat_container = st.container(height=350)
    with chat_container:
        if not st.session_state["chat_history"]:
            st.info("👋 안녕하세요! 풀이 과정 중 궁금한 점(예: Step 2에서 극값 구하는 이유)을 물어보세요.")
        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    # 질문 입력창
    user_query = st.chat_input("질문을 입력하세요...")
    if user_query:
        st.session_state["chat_history"].append({"role": "user", "content": user_query})
        
        active_key = st.session_state.get("api_key", "").strip()
        if not active_key:
            st.session_state["chat_history"].append({"role": "assistant", "content": "⚠️ 먼저 사이드바에 API Key를 입력해 주세요!"})
        else:
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
            
            try:
                res = tutor_model.generate_content(tutor_prompt)
                st.session_state["chat_history"].append({"role": "assistant", "content": res.text})
            except Exception as e:
                st.session_state["chat_history"].append({"role": "assistant", "content": f"답변 생성 오류: {e}"})
        
        st.rerun()
