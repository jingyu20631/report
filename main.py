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
st.caption("내 API 키에서 이용 가능한 최적의 Gemini AI 모델을 자동 감지하여 문제 풀이와 시각화를 제공합니다.")

# -------------------------------------------------------------------
# 사이드바: API 키 및 사용 가능한 모델 동적 자동 탐색
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

# 실제 호출 가능한 모델 자동 수집 및 Flash 최우선 정렬
valid_models = []
if st.session_state["api_key"]:
    try:
        genai.configure(api_key=st.session_state["api_key"])
        
        raw_models = []
        for m in genai.list_models():
            # 이미지와 텍스트 분석이 가능한 generateContent 모델만 필터링
            if "generateContent" in m.supported_generation_methods:
                name = m.name.replace("models/", "")
                if "gemini" in name and not any(x in name for x in ["embedding", "bison", "imagen"]):
                    raw_models.append(name)

        # 1순위: 속도/쿼터가 우수한 Flash 계열 모델 우선 배치
        flash_models = [m for m in raw_models if "flash" in m.lower()]
        other_models = [m for m in raw_models if "flash" not in m.lower()]
        
        valid_models = flash_models + other_models
        
        if valid_models:
            st.sidebar.success(f"✅ 사용 가능한 모델 {len(valid_models)}개 감지 완료")
        else:
            st.sidebar.warning("⚠️ 이미지 분석이 가능한 Gemini 모델을 찾지 못했습니다.")
    except Exception as e:
        st.sidebar.error(f"API 키 확인 실패: {e}")

if valid_models:
    selected_model = st.sidebar.selectbox("사용 가능한 AI 모델 목록", valid_models, index=0)

    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 선택된 모델 정보")
    m_lower = selected_model.lower()
    if "flash" in m_lower:
        st.sidebar.markdown(f"**모델명:** `{selected_model}`")
        st.sidebar.markdown("⚡ **특성:** 빠름 & 무료 쿼터 안정적")
    else:
        st.sidebar.markdown(f"**모델명:** `{selected_model}`")
        st.sidebar.markdown("🧠 **특성:** 정교한 추론 (요청 한도 주의)")
else:
    selected_model = None
    st.sidebar.info("💡 사이드바에 유효한 Gemini API Key를 입력해 주세요.")

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
# 문제 분석 및 자동 모델 폴백(Fallback) 실행 로직
# -------------------------------------------------------------------
if uploaded_image:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🖼️ 업로드된 문제")
        st.image(uploaded_image, use_container_width=True)

    with col2:
        st.subheader("🚀 문제 분석 및 시각화")
        if selected_model:
            st.write(f"현재 선택된 모델: **`{selected_model}`**")
        solve_button = st.button("✨ AI 풀이 & 그래프 그리기", type="primary", use_container_width=True)

    if solve_button:
        active_api_key = st.session_state.get("api_key", "").strip()

        if not active_api_key or not selected_model:
            st.error("⚠️ API Key를 입력하고 목록에서 모델을 선택해 주세요.")
        else:
            with st.spinner(f"[{selected_model}] 모델이 분석을 진행 중입니다..."):
                genai.configure(api_key=active_api_key)
                
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
                   - 맨 마지막에 plt.show() 대신 fig 객체 사용
                """

                # 모델 자동 전환(Fallback) 시도
                response_text = None
                trials = [selected_model] + [m for m in valid_models if m != selected_model]

                for model_candidate in trials:
                    try:
                        model = genai.GenerativeModel(model_candidate)
                        response = model.generate_content([prompt, uploaded_image])
                        response_text = response.text
                        break # 성공 시 루프 탈출
                    except Exception as err:
                        err_str = str(err)
                        if "429" in err_str or "404" in err_str or "Quota" in err_str:
                            st.warning(f"⚠️ `{model_candidate}` 모델 요청 실패(쿼터/지지원). 다음 사용 가능 모델로 재시도합니다...")
                            continue
                        else:
                            st.error(f"오류 발생: {err}")
                            break

                if response_text:
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
                else:
                    st.error("🚨 모든 모델에서 요율 초과(429) 또는 오류가 발생했습니다. 잠시 후 다시 시도하거나 새 API 키를 입력해 보세요.")
