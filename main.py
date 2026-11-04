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
    "미적분 문제 사진을 올리면 최고 성능 Gemini 모델이 상세 풀이와 함께 그래프 및 핵심 단서(극점, 접선, 적분구간 등)를 시각화합니다."
)

# 사이드바 설정
st.sidebar.header("⚙️ 모델 & API 설정")
api_key = st.sidebar.text_input(
    "Google Gemini API Key",
    type="password",
    help="Google AI Studio(aistudio.google.com)에서 무료 발급 가능합니다.",
)

# 최고 성능 모델 선택 (기본값: gemini-1.5-pro)
selected_model = st.sidebar.selectbox(
    "사용할 AI 모델 선택",
    ["gemini-1.5-pro", "gemini-1.5-flash"],
    index=0,
    help="gemini-1.5-pro는 수시/수능 최고난도 미적분 문제 추론 및 수식 분석에 특화된 최고 성능 모델입니다.",
)

# 입력 방식 선택
input_method = st.radio(
    "사진 입력 방식 선택", ["파일 업로드", "카메라 촬영"], horizontal=True
)

uploaded_image = None
if input_method == "파일 업로드":
    uploaded_file = st.file_uploader(
        "미적분 문제 사진 선택 (JPG, PNG)", type=["jpg", "jpeg", "png"]
    )
    if uploaded_file:
        uploaded_image = Image.open(uploaded_file)
else:
    camera_file = st.camera_input("문제 사진 촬영")
    if camera_file:
        uploaded_image = Image.open(camera_file)

# 처리 메인 로직
if uploaded_image:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🖼️ 분석할 문제 사진")
        st.image(uploaded_image, use_container_width=True)

    with col2:
        st.subheader("🚀 문제 분석 및 시각화")
        st.write(
            "선택한 모델이 문제의 수식, 극점, 변곡점, 정적분 영역 등을 계산하고 시각화 코드까지 생성합니다."
        )
        solve_button = st.button(
            "✨ AI 풀이 & 그래프 그리기", type="primary", use_container_width=True
        )

    if solve_button:
        if not api_key:
            st.error("⚠️ 사이드바에 Google Gemini API Key를 입력해 주세요.")
        else:
            with st.spinner(
                f"{selected_model} 모델이 문제를 분석하고 수식을 그래프로 시각화하는 중입니다..."
            ):
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(selected_model)

                    prompt = """
                    너는 최고의 미적분 수학 교사이자 데이터 시각화 전문가야.
                    제공된 이미지의 미적분 문제(극한, 미분, 극값, 변곡점, 접선, 정적분, 넓이/부피 등)를 분석하고 답변해줘.

                    [답변 형식 작성 규칙]
                    1. 📌 **문제 요약 및 조건 분석**: 주어진 함수 및 핵심 조건 정리
                    2. 💡 **출제 의도 및 관련 개념**: 사용되는 핵심 미적분 개념 및 공식 (Latex 수식 사용)
                    3. 📝 **단계별 상세 풀이**: Step 1, Step 2 순서대로 논리적이고 정교하게 풀이 과정 제시
                    4. ✅ **최종 정답**: 정답을 명확히 강조

                    5. 📊 **Matplotlib 그래프 작성 코드를 반드시 아래형식대로 포함해줘**:
                       - 문제의 함수 f(x), 도함수, 접선, 정적분 영역 등을 시각화하는 파이썬 코드를 작성해.
                       - 코드 블록은 반드시 ```python 으로 시작하고 ``` 로 끝내야 해.
                       - 코드 규칙:
                         * numpy와 matplotlib.pyplot을 사용해.
                         * 문제에서 중요한 단서(극대/극소, 변곡점, x/y절편, 접점, 정적분 구간 등)는 plt.scatter()와 plt.annotate()로 좌표와 명칭을 그래프 위에 명확히 표시해.
                         * 필요시 plt.fill_between()으로 정적분 넓이 영역을 칠해줘.
                         * plt.grid(True), plt.axhline(0, color='black', lw=1), plt.axvline(0, color='black', lw=1)을 기본으로 포함해.
                         * 한글 깨짐을 방지하기 위해 그래프 텍스트 및 라벨은 알파벳/수식(예: f(x), x, y, Local Max (2, 4)) 형태로 작성해줘.
                         * 맨 마지막에 plt.show()를 호출하지 말고 fig 객체가 생성되도록 해줘.
                    """

                    response = model.generate_content([prompt, uploaded_image])
                    response_text = response.text

                    st.divider()

                    # 1. 텍스트 해설 출력
                    st.subheader("📖 AI 미적분 상세 해설")
                    st.markdown(response_text)

                    # 2. 파이썬 코드 추출 및 그래프 실행
                    st.divider()
                    st.subheader("📈 미적분 함수 & 핵심 단서 시각화 그래프")

                    code_match = re.search(
                        r"```python(.*?)```", response_text, re.DOTALL
                    )

                    if code_match:
                        python_code = code_match.group(1).strip()

                        # 실행용 안전한 scope 설정
                        fig, ax = plt.subplots(figsize=(8, 5))
                        local_scope = {"np": np, "plt": plt, "fig": fig, "ax": ax}

                        try:
                            # 코드 실행
                            exec(python_code, local_scope)

                            # Matplotlib figure가 파이썬 코드로 그려졌는지 확인 후 Streamlit 출력
                            st.pyplot(plt.gcf())
                            plt.close("all")
                        except Exception as plot_err:
                            st.warning(
                                f"그래프 자동 생성 중 오류가 발생했습니다: {plot_err}"
                            )
                            with st.expander("생성된 파이썬 코드 보기"):
                                st.code(python_code, language="python")
                    else:
                        st.info(
                            "이 문제에는 시각화 코드가 생성되지 않았거나 텍스트 위주의 문제 형태입니다."
                        )

                except Exception as e:
                    st.error(f"오류 발생: {e}")
