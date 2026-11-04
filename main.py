import re
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import google.generativeai as genai
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="고성능 AI 미적분 풀이 & 시각화 헬퍼", page_icon="📐", layout="wide"
)

st.title("📐 고성능 AI 미적분 풀이 & 그래프 시각화 헬퍼")
st.caption(
    "미적분 문제 사진을 올리면 AI가 상세 풀이와 함께 그래프 및 핵심 단서(극점, 접선, 정적분 구간 등)를 시각화합니다."
)

# -------------------------------------------------------------------
# 사이드바: API 키 및 모델 설정
# -------------------------------------------------------------------
st.sidebar.header("🔑 API 및 모델 설정")

if "api_key" not in st.session_state:
    st.session_state["api_key"] = ""

api_key_input = st.sidebar.text_input(
    "Google Gemini API Key 입력",
    value=st.session_state["api_key"],
    type="password",
    help="Google AI Studio(aistudio.google.com)에서 무료로 발급할 수 있습니다.",
)

if api_key_input:
    st.session_state["api_key"] = api_key_input
    st.sidebar.success("✅ API 키가 설정되었습니다.")

# 안정적인 기본 모델 목록 (에러 방지용 -latest 식별자 사용)
default_models = {
    "Gemini 1.5 Flash (⚡ 추천: 빠르고 정확함)": "gemini-1.5-flash-latest",
    "Gemini 2.0 Flash (🚀 최신 초고속 모델)": "gemini-2.0-flash",
    "Gemini 1.5 Pro (🧠 고난도 킬러문항 전용)": "gemini-1.5-pro-latest",
}

# API 키가 입력되었을 경우 실제 호출 가능한 모델 목록 가져오기 시도
available_models = default_models
if st.session_state["api_key"]:
    try:
        genai.configure(api_key=st.session_state["api_key"])
        fetched_models = {}
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods and "gemini" in m.name:
                clean_name = m.name.replace("models/", "")
                fetched_models[f"{clean_name}"] = clean_name
        if fetched_models:
            available_models = fetched_models
    except Exception:
        pass  # 조회 실패 시 기본 안전 목록 사용

selected_label = st.sidebar.selectbox("AI 모델 선택", list(available_models.keys()), index=0)
selected_model = available_models[selected_label]

st.sidebar.markdown("---")
st.sidebar.write("💡 **사용 가이드**")
st.sidebar.write("1. API 키 입력 후 **Flash** 계열 모델을 선택하면 빠른 풀이가 진행됩니다.")
st.sidebar.write("2. 수식과 그래프가 또렷하게 보이도록 정면 사진을 올려주세요.")

# -------------------------------------------------------------------
# 메인화면: 사진 입력
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
# AI 분석 및 시각화 로직
# -------------------------------------------------------------------
if uploaded_image:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🖼️ 업로드된 문제")
        st.image(uploaded_image, use_container_width=True)

    with col2:
        st.subheader("🚀 문제 분석 및 시각화")
        st.write(f"선택된 모델: **{selected_model}**")
        solve_button = st.button("✨ AI 풀이 & 그래프 그리기", type="primary", use_container_width=True)

    if solve_button:
        active_api_key = st.session_state.get("api_key", "").strip()

        if not active_api_key:
            st.error("⚠️ 사이드바에 Google Gemini API Key를 입력해 주세요.")
        else:
            with st.spinner(f"[{selected_model}] 모델이 풀이 및 그래프 코드를 생성 중입니다..."):
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
                       - 문제에 등장하는 함수 f(x), 도함수, 접선, 또는 정적분 영역을 시각화하는 파이썬 코드를 포함해.
                       - 코드 블록은 반드시 ```python 로 시작하고 ``` 로 끝내야 해.
                       - 코드 작성 조건:
                         * numpy와 matplotlib.pyplot을 사용해.
                         * 문제의 핵심 단서(극대/극소, 변곡점, x/y절편, 접점, 정적분 구간 등)는 plt.scatter()와 plt.annotate()로 좌표 및 라벨을 그래프 위에 명확히 표시해.
                         * 필요시 plt.fill_between()으로 정적분 넓이 영역을 색칠해.
                         * plt.grid(True), plt.axhline(0, color='black', lw=1), plt.axvline(0, color='black', lw=1)을 기본으로 포함해.
                         * 한글 깨짐 방지를 위해 그래프 내부 라벨은 영문/수식(예: f(x), x, y, Local Max (2, 4))으로 작성해줘.
                         * 맨 마지막에 plt.show()를 쓰지 말고 fig 객체가 생성되도록 해줘.
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
                        st.info("이 문제에는 그래프 시각화 코드가 포함되지 않았습니다.")

                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")
