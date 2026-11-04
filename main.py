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
st.caption("미적분 문제 사진을 올리면 최신 Gemini AI가 풀이와 그래프 핵심 단서를 시각화합니다.")

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

# 최신 안정화 및 최신 프리뷰 모델 라인업
RECOMMENDED_MODELS = [
    "gemini-1.5-flash",
    "gemini-2.5-flash",
    "gemini-3.1-pro-preview",
    "gemini-1.5-pro",
    "직접 입력..."
]

available_models = []
if st.session_state["api_key"]:
    try:
        genai.configure(api_key=st.session_state["api_key"])
        fetched = []
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                name = m.name.replace("models/", "")
                # 404/Quota 에러 빈도가 높은 구형/특수 모델 제외
                if "gemini" in name and not any(x in name for x in ["image", "bison", "embedding", "2.5-pro"]):
                    fetched.append(name)
        
        # 권장 목록과 동적 로딩 목록 결합
        for r in RECOMMENDED_MODELS:
            if r not in available_models:
                available_models.append(r)
        for f in fetched:
            if f not in available_models:
                available_models.append(f)
                
        st.sidebar.success("✅ API 연결 완료")
    except Exception as e:
        available_models = RECOMMENDED_MODELS
        st.sidebar.error(f"API 확인 실패: {e}")
else:
    available_models = RECOMMENDED_MODELS

selected_option = st.sidebar.selectbox("사용할 AI 모델 선택", available_models, index=0)

if selected_option == "직접 입력...":
    selected_model = st.sidebar.text_input("모델명 직접 입력 (예: gemini-3.1-pro-preview)", value="gemini-1.5-flash")
else:
    selected_model = selected_option

# 모델 속성 안내
st.sidebar.markdown("---")
st.sidebar.subheader("📋 선택된 모델 정보")
m_lower = selected_model.lower()
if "flash" in m_lower:
    st.sidebar.markdown("⚡ **속도:** 매우 빠름 (무료 쿼터 안정적)")
    st.sidebar.markdown("💡 **추천:** 일반 내신/모의고사 미적분 풀이")
elif "pro" in m_lower or "preview" in m_lower:
    st.sidebar.markdown("🧠 **속도:** 둔함 (고성능 추론)")
    st.sidebar.markdown("💡 **추천:** 고난도 킬러문항 및 정밀 그래프 생성")
else:
    st.sidebar.markdown("⚙️ **속도:** 범용 모델")

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
# 풀이 및 404/429 예외 처리 로직
# -------------------------------------------------------------------
if uploaded_image:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🖼️ 업로드된 문제")
        st.image(uploaded_image, use_container_width=True)

    with col2:
        st.subheader("🚀 문제 분석 및 시각화")
        st.write(f"가동 대상 모델: **`{selected_model}`**")
        solve_button = st.button("✨ AI 풀이 & 그래프 그리기", type="primary", use_container_width=True)

    if solve_button:
        active_api_key = st.session_state.get("api_key", "").strip()

        if not active_api_key:
            st.error("⚠️ 사이드바에 API Key를 먼저 입력해 주세요!")
        else:
            with st.spinner(f"[{selected_model}] 모델이 분석 및 시각화 코드를 작성 중입니다..."):
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
                       - 코드 블록은 반드시 ```python 로 시작하고 ``` 로 끝내야 함
                       - 한글 깨짐 방지를 위해 그래프 내부 라벨은 영문/수식(예: f(x), Local Max (2, 4)) 사용
                       - 맨 마지막에 plt.show()를 쓰지 말고 fig 객체 사용
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
                            st.warning(f"그래프 코드 실행 오류: {plot_err}")
                            with st.expander("생성된 파이썬 코드 확인"):
                                st.code(python_code, language="python")
                    else:
                        st.info("이 문제에는 그래프 시각화 코드가 생성되지 않았습니다.")

                except Exception as e:
                    err_msg = str(e)
                    if "404" in err_msg or "not found" in err_msg.lower():
                        st.error(f"🚨 선택한 모델(`{selected_model}`)이 지원 중단되었거나 사용할 수 없는 모델입니다.")
                        st.warning("사이드바에서 **`gemini-1.5-flash`** 또는 **`gemini-3.1-pro-preview`**로 변경 후 다시 시도하세요.")
                    elif "429" in err_msg or "Quota exceeded" in err_msg:
                        st.error("🚨 API 무료 사용량(Quota)을 초과했습니다.")
                        st.warning("사이드바에서 **`gemini-1.5-flash`**를 선택하거나 새 API Key를 입력하세요.")
                    else:
                        st.error(f"오류 발생: {e}")
