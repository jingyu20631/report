import re
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import google.generativeai as genai
import streamlit as st

st.set_page_config(
    page_title="고성능 AI 미적분 풀이 & 시각화 헬퍼",
    page_icon="📐",
    layout="wide"
)

st.title("📐 고성능 AI 미적분 풀이 & 그래프 시각화 헬퍼")
st.caption("문제 사진을 올리면 API에서 감지된 Gemini 모델이 풀이와 핵심 단서를 시각화합니다.")

# -------------------------------------------------------------------
# 사이드바: API 키 및 무료 플랜 추천 모델 로딩
# -------------------------------------------------------------------
st.sidebar.header("🔑 API 및 모델 설정")

if "api_key" not in st.session_state:
    st.session_state["api_key"] = ""

api_key_input = st.sidebar.text_input(
    "Google Gemini API Key 입력",
    value=st.session_state["api_key"],
    type="password",
    help="Google AI Studio(aistudio.google.com)에서 발급받은 키를 입력하세요."
)

if api_key_input:
    st.session_state["api_key"] = api_key_input.strip()

# 무료 티어에서 안정적인 모델 위주로 필터링
available_models = []
if st.session_state["api_key"]:
    try:
        genai.configure(api_key=st.session_state["api_key"])
        
        # 기본 추천 우선순위 모델
        priority_models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
        
        fetched_models = []
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                name = m.name.replace("models/", "")
                # 쿼터 오류가 잦은 3-pro-image, experimental, embedding 모델 제외
                if "gemini" in name and not any(x in name for x in ["image", "exp", "embedding", "bison"]):
                    fetched_models.append(name)

        # 우선순위 모델을 맨 앞으로 정렬
        for p in priority_models:
            if p in fetched_models:
                available_models.append(p)
        for f in fetched_models:
            if f not in available_models:
                available_models.append(f)

        if available_models:
            st.sidebar.success(f"✅ 안정적인 모델 {len(available_models)}개 감지됨")
        else:
            st.sidebar.warning("⚠️ 사용 가능한 Gemini 모델을 찾지 못했습니다.")
    except Exception as e:
        st.sidebar.error(f"API 키 검증 실패: {e}")

if available_models:
    selected_model = st.sidebar.selectbox("사용할 AI 모델 선택 (Flash 추천)", available_models, index=0)

    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 선택된 모델 정보")
    
    model_lower = selected_model.lower()
    if "flash" in model_lower:
        speed = "⚡⚡⚡ 매우 빠름 (무료 쿼터 넉넉함)"
        desc = "무료 요금제 사용 시 가장 안정적이고 빠른 모델"
    elif "pro" in model_lower:
        speed = "🧠🐢 둔함 (일일 제한 엄격)"
        desc = "고난도 추론용 (무료 요금제 시 429 오류 가능성 있음)"
    else:
        speed = "⚡ 표준"
        desc = "일반 Gemini 처리 모델"

    st.sidebar.markdown(f"**모델명:** `{selected_model}`")
    st.sidebar.markdown(f"**상태:** {speed}")
    st.sidebar.markdown(f"ℹ️ **설명:** {desc}")
else:
    selected_model = None
    st.sidebar.info("💡 사이드바에 유효한 Gemini API Key를 입력하세요.")

# -------------------------------------------------------------------
# 메인 화면: 사진 입력
# -------------------------------------------------------------------
input_method = st.radio("사진 입력 방식 선택", ["파일 업로드", "카메라 직접 촬영"], horizontal=True)

uploaded_image = None
if input_method == "파일 업로드":
    uploaded_file = st.file_uploader("미적분 문제 사진 선택 (JPG, PNG)", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        uploaded_image = Image.open(uploaded_file)
else:
    camera_file = st.camera_input("문제 사진 촬영")
    if camera_file:
        uploaded_image = Image.open(camera_file)

# -------------------------------------------------------------------
# 풀이 및 예외 처리 강화 로직
# -------------------------------------------------------------------
if uploaded_image:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🖼️ 업로드된 문제")
        st.image(uploaded_image, use_container_width=True)

    with col2:
        st.subheader("🚀 문제 분석 및 시각화")
        st.write(f"현재 선택된 모델: **{selected_model}**")
        solve_button = st.button("✨ AI 풀이 & 그래프 그리기", type="primary", use_container_width=True)

    if solve_button:
        active_api_key = st.session_state.get("api_key", "").strip()

        if not active_api_key or not selected_model:
            st.error("⚠️ API Key를 입력하고 사용 가능한 모델을 선택해 주세요.")
        else:
            with st.spinner(f"[{selected_model}] 모델로 분석하는 중입니다..."):
                try:
                    genai.configure(api_key=active_api_key)
                    model = genai.GenerativeModel(selected_model)

                    prompt = """
                    너는 최고의 미적분 수학 교사이자 데이터 시각화 전문가야.
                    제공된 이미지의 미적분 문제(도함수, 극값, 변곡점, 접선, 정적분, 넓이 등)를 분석하고 답변해줘.

                    [답변 형식 규칙]
                    1. 📌 **문제 요약 및 핵심 조건**: 주어진 함수와 구하고자 하는 값 정리
                    2. 💡 **출제 의도 및 관련 개념**: 사용되는 핵심 미적분 개념/공식 (Latex 수식 표기)
                    3. 📝 **단계별 상세 풀이**: Step 1, Step 2 순서대로 논리적으로 풀이
                    4. ✅ **최종 정답**: 정답을 명확히 강조

                    5. 📊 **Matplotlib 그래프 작성 파이썬 코드를 반드시 작성해줘**:
                       - 문제의 함수 f(x), 접선, 정적분 영역 시각화
                       - ```python 코드로 작성하고 plt.show() 대신 fig/ax 객체 활용
                       - 한글 깨짐 방지를 위해 라벨은 영문/수식(예: f(x), Local Max (2, 4)) 사용
                    """

                    response = model.generate_content([prompt, uploaded_image])
                    response_text = response.text

                    st.divider()
                    st.subheader("📖 AI 미적분 상세 해설")
                    st.markdown(response_text)

                    st.divider()
                    st.subheader("📈 미적분 함수 & 핵심 단서 시각화 그래프")

                    code_match = re.search(r"```python(.*?)```", response_text, re.DOTALL)

                    if code_match:
                        python_code = code_match.group(1).strip()
                        fig, ax = plt.subplots(figsize=(8, 5))
                        local_scope = {"np": np, "plt": plt, "fig": fig, "ax": ax}

                        try:
                            exec(python_code, local_scope)
                            st.pyplot(plt.gcf())
                            plt.close("all")
                        except Exception as plot_err:
                            st.warning(f"그래프 코드 실행 중 오류가 발생했습니다: {plot_err}")
                            with st.expander("생성된 파이썬 코드 확인"):
                                st.code(python_code, language="python")
                    else:
                        st.info("이 문제에는 그래프 시각화 코드가 생성되지 않았습니다.")

                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg or "Quota exceeded" in err_msg:
                        st.error("🚨 **API 일일/분당 사용량(Quota) 초과 오류가 발생했습니다.**")
                        st.warning("""
                        **해결 방법:**
                        1. 사이드바에서 모델을 **`gemini-1.5-flash`**로 변경한 후 다시 시도하세요.
                        2. [Google AI Studio](https://aistudio.google.com/)에서 새로운 API Key를 발급받아 입력하세요.
                        """)
                    else:
                        st.error(f"오류가 발생했습니다: {e}")
