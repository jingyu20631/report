import re
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import google.generativeai as genai
import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="고성능 AI 미적분 풀이 & 시각화 헬퍼",
    page_icon="📐",
    layout="wide"
)

st.title("📐 고성능 AI 미적분 풀이 & 그래프 시각화 헬퍼")
st.caption("문제 사진을 올리면 AI가 풀이와 핵심 단서(극점, 접선, 정적분 영역)를 시각화합니다.")

# -------------------------------------------------------------------
# AI 모델별 특성 및 장단점 DB (짧고 명확한 요약)
# -------------------------------------------------------------------
MODEL_INFO = {
    "gemini-1.5-flash": {
        "name": "Gemini 1.5 Flash",
        "speed": "⚡⚡⚡ 매우 빠름",
        "desc": "일반적인 내신 및 모의고사 미적분 문제 풀이에 최적화된 표준 모델.",
        "pros": "응답 속도가 2~3초로 매우 빠르고, 그래프 코드 생성 성공률이 안정적임.",
        "cons": "수능 21, 30번급 극악 난이도 문제는 복잡한 추론 과정에서 오류가 날 수 있음."
    },
    "gemini-2.0-flash": {
        "name": "Gemini 2.0 Flash",
        "speed": "🚀🚀🚀 초고속 + 최신",
        "desc": "속도와 수식 추론 능력을 대폭 끌어올린 차세대 실시간 처리 모델.",
        "pros": "이미지 인식 정확도가 높고 복잡한 연산을 빠르게 다룸.",
        "cons": "최신 모델 특성상 일부 API 환경에서 쿼터 제한이 더 타이트할 수 있음."
    },
    "gemini-1.5-pro": {
        "name": "Gemini 1.5 Pro",
        "speed": "🧠🐢 둔하지만 정교함",
        "desc": "수능 킬러문항, 경시대회급 고난도 미적분 조건 분석 전용 지능형 모델.",
        "pros": "복잡한 미적분 정의, 변곡점 추론, 정밀한 단계별 논리가 매우 뛰어남.",
        "cons": "답변 생성까지 10~20초 이상 소요되며 API 일일 호출 제한량이 적음."
    }
}

# -------------------------------------------------------------------
# 사이드바: API 키 및 모델 선택
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
    st.sidebar.success("✅ API 키 설정 완료")

# 1. 사용할 수 있는 미적분 추천 모델 목록 정리
selectable_models = list(MODEL_INFO.keys())

# API 키가 있으면 사용 가능한 모델을 자동 필터링하여 동적 추가
if st.session_state["api_key"]:
    try:
        genai.configure(api_key=st.session_state["api_key"])
        active_list = []
        for m in genai.list_models():
            # 텍스트/이미지 기반 풀이가 가능한 generateContent 지원 모델만 추출
            if "generateContent" in m.supported_generation_methods and "gemini" in m.name:
                name_clean = m.name.replace("models/", "")
                # 임베딩/오디오 모델 제외
                if not any(x in name_clean for x in ["embedding", "bison", "imagen", "audio"]):
                    active_list.append(name_clean)
        
        # 목록 합치기 (추천 모델 우선 배치를 위해 중복 제거 유지를 적용)
        for act in active_list:
            if act not in selectable_models and ("flash" in act or "pro" in act):
                selectable_models.append(act)
    except Exception:
        pass

# 2. 모델 선택 드롭다운
selected_model = st.sidebar.selectbox("사용할 AI 모델 선택", selectable_models, index=0)

# 3. 선택한 모델 장단점 카드 출력
st.sidebar.markdown("---")
st.sidebar.subheader("📋 선택한 AI 정보")

info = MODEL_INFO.get(selected_model, {
    "name": selected_model,
    "speed": "⚡ 표준",
    "desc": "사용자 API 키 목록에서 자동 감지된 Gemini 모델입니다.",
    "pros": "기본 수식 및 이미지 추론이 가능합니다.",
    "cons": "고난도 문제의 경우 답변 속도와 정확도가 다를 수 있습니다."
})

st.sidebar.markdown(f"**모델명:** `{info['name']}`")
st.sidebar.markdown(f"**속도:** {info['speed']}")
st.sidebar.markdown(f"ℹ️ **설명:** {info['desc']}")
st.sidebar.markdown(f"👍 **장점:** {info['pros']}")
st.sidebar.markdown(f"👎 **단점:** {info['cons']}")

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
        st.write(f"현재 가동 중인 모델: **{selected_model}**")
        solve_button = st.button("✨ AI 풀이 & 그래프 그리기", type="primary", use_container_width=True)

    if solve_button:
        active_api_key = st.session_state.get("api_key", "").strip()

        if not active_api_key:
            st.error("⚠️ 사이드바에 API Key를 먼저 입력해 주세요!")
        else:
            with st.spinner(f"[{selected_model}] 모델이 분석 및 그래프 코드를 생성 중입니다..."):
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
