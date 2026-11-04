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
# 사이드바: API 키 입력 및 실제 API 동적 모델 로딩
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

# 실제 API 키에 할당된 모델 목록 동적 조회
available_models = []
if st.session_state["api_key"]:
    try:
        genai.configure(api_key=st.session_state["api_key"])
        # generateContent를 지원하는 gemini 계열 모델만 자동 필터링
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                model_name = m.name.replace("models/", "")
                if model_name.startswith("gemini"):
                    available_models.append(model_name)
        
        if available_models:
            st.sidebar.success(f"✅ 사용 가능한 모델 {len(available_models)}개 감지됨")
        else:
            st.sidebar.warning("⚠️ 사용 가능한 Gemini 모델을 찾지 못했습니다.")
    except Exception as e:
        st.sidebar.error(f"API 키 확인 실패: {e}")

# API 키 입력 전 안내 또는 모델 선택 드롭다운
if available_models:
    selected_model = st.sidebar.selectbox("사용 가능한 AI 모델 선택", available_models, index=0)

    # 선택된 모델의 키워드(Flash/Pro 등) 기반 속성 및 장단점 자동 요약
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 선택된 모델 속성")

    model_lower = selected_model.lower()
    if "flash" in model_lower:
        speed = "⚡⚡⚡ 매우 빠름"
        desc = "경량화된 실시간 처리 모델"
        pros = "빠른 텍스트/이미지 응답 속도 및 높은 안정성"
        cons = "초고난도 복합 추론 문제는 단계별 검증이 필요할 수 있음"
    elif "pro" in model_lower:
        speed = "🧠🐢 둔하지만 정교함"
        desc = "심층 추론 및 논리 연산 전문 모델"
        pros = "킬러문항, 조건 분석, 정밀 수식 및 코드 생성에 강함"
        cons = "응답 완료까지 상대적으로 시간이 더 오래 걸림"
    else:
        speed = "⚡ 표준"
        desc = "범용 Gemini 처리 모델"
        pros = "기본적인 이미지 인식 및 풀이 능력 지원"
        cons = "모델 특성에 따라 응답 속도가 다를 수 있음"

    st.sidebar.markdown(f"**모델명:** `{selected_model}`")
    st.sidebar.markdown(f"**속도:** {speed}")
    st.sidebar.markdown(f"ℹ️ **설명:** {desc}")
    st.sidebar.markdown(f"👍 **장점:** {pros}")
    st.sidebar.markdown(f"👎 **단점:** {cons}")

else:
    selected_model = None
    st.sidebar.info("💡 사이드바에 유효한 Gemini API Key를 입력하면 목록이 표시됩니다.")

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
# 풀이 및 시각화 로직
# -------------------------------------------------------------------
if uploaded_image:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🖼️ 업로드된 문제")
        st.image(uploaded_image, use_container_width=True)

    with col2:
        st.subheader("🚀 문제 분석 및 시각화")
        if selected_model:
            st.write(f"현재 선택된 모델: **{selected_model}**")
        else:
            st.write("선택된 모델 없음 (API 키 필요)")

        solve_button = st.button("✨ AI 풀이 & 그래프 그리기", type="primary", use_container_width=True)

    if solve_button:
        active_api_key = st.session_state.get("api_key", "").strip()

        if not active_api_key or not selected_model:
            st.error("⚠️ API Key를 입력하고 사용 가능한 모델을 선택해 주세요.")
        else:
            with st.spinner(f"[{selected_model}] 모델이 문제와 그래프를 분석하는 중입니다..."):
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
                            st.warning(f"그래프 시각화 코드 실행 중 오류가 발생했습니다: {plot_err}")
                            with st.expander("생성된 파이썬 코드 확인"):
                                st.code(python_code, language="python")
                    else:
                        st.info("이 문제에는 그래프 시각화 코드가 생성되지 않았거나 수식 중심 문제입니다.")

                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")
