import streamlit as st
import speech_recognition as sr
import os
import tempfile
import datetime
from supabase import create_client
from dotenv import load_dotenv
import json

# 환경 변수 로드
load_dotenv()

# Supabase 클라이언트 설정
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

# Supabase 연결 확인 및 클라이언트 생성
try:
    if supabase_url and supabase_key and supabase_url != "your_supabase_url" and supabase_key != "your_supabase_key":
        # 버전 호환성 문제로 인해 옵션 없이 생성
        supabase = create_client(supabase_url, supabase_key)
        supabase_connected = True
    else:
        supabase_connected = False
except TypeError as e:
    st.error(f"Supabase 연결 오류: {str(e)}")
    st.info("Supabase 라이브러리 버전 문제일 수 있습니다. 'pip install supabase==1.0.3'을 실행해보세요.")
    supabase_connected = False

# 페이지 설정
st.set_page_config(
    page_title="음성 메모 앱",
    page_icon="🎤",
    layout="centered"
)

# 앱 제목
st.title("🎤 음성 메모 앱")

# 세션 상태 초기화
if 'text' not in st.session_state:
    st.session_state.text = ""
if 'recording' not in st.session_state:
    st.session_state.recording = False
if 'audio_file' not in st.session_state:
    st.session_state.audio_file = None

# 음성을 텍스트로 변환하는 함수
def speech_to_text(audio_file):
    r = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio_data = r.record(source)
        try:
            text = r.recognize_google(audio_data, language='ko-KR')
            return text
        except sr.UnknownValueError:
            return "음성을 인식할 수 없습니다."
        except sr.RequestError:
            return "Google API 요청 중 오류가 발생했습니다."

# Supabase 테이블 생성 함수
def create_table_if_not_exists():
    if not supabase_connected:
        return False
    
    try:
        # 테이블이 존재하는지 확인
        response = supabase.table('voice_memos').select('id').limit(1).execute()
        return True
    except Exception as e:
        # 테이블이 없으면 생성
        try:
            # RPC 호출을 통해 테이블 생성 (Supabase에서는 직접 CREATE TABLE을 실행할 수 없음)
            # 실제로는 Supabase 대시보드에서 테이블을 생성하거나 마이그레이션 스크립트를 사용하는 것이 좋습니다.
            # 이 예제에서는 테이블이 이미 존재한다고 가정합니다.
            st.warning("Supabase에 'voice_memos' 테이블이 없습니다. Supabase 대시보드에서 테이블을 생성해주세요.")
            return False
        except Exception as create_error:
            st.error(f"테이블 생성 중 오류 발생: {str(create_error)}")
            return False

# Supabase에 메모 저장 함수
def save_memo_to_supabase(text):
    if not supabase_connected:
        st.error("Supabase 연결 정보가 올바르게 설정되지 않았습니다. .env 파일을 확인해주세요.")
        return False
    
    if not create_table_if_not_exists():
        return False
    
    try:
        # 현재 시간 가져오기
        current_time = datetime.datetime.now().isoformat()
        
        # Supabase에 데이터 삽입
        data = {
            "content": text,
            "created_at": current_time
        }
        
        response = supabase.table('voice_memos').insert(data).execute()
        
        if response.data:
            return True
        else:
            st.error("데이터 저장 중 오류가 발생했습니다.")
            return False
    except Exception as e:
        st.error(f"Supabase 저장 중 오류 발생: {str(e)}")
        return False

# 메인 UI
col1, col2 = st.columns(2)

with col1:
    # 녹음 버튼
    if not st.session_state.recording:
        if st.button("녹음 시작"):
            st.session_state.recording = True
            st.experimental_rerun()
    else:
        if st.button("녹음 중지"):
            st.session_state.recording = False
            st.experimental_rerun()

with col2:
    # 저장 버튼
    if st.session_state.text:
        if st.button("텍스트 저장"):
            if save_memo_to_supabase(st.session_state.text):
                st.success("메모가 성공적으로 저장되었습니다!")
                # 저장 후 텍스트 초기화
                st.session_state.text = ""
                st.experimental_rerun()

# 녹음 상태 표시
if st.session_state.recording:
    st.warning("녹음 중... 말씀하신 후 '녹음 중지' 버튼을 클릭하세요.")
    # 실제 녹음 기능 (Streamlit에서는 직접 마이크 접근이 제한적이므로 파일 업로드로 대체)
    st.info("Streamlit에서는 직접 마이크 접근이 제한적입니다. 녹음된 오디오 파일을 업로드해주세요.")
    uploaded_file = st.file_uploader("오디오 파일 업로드 (.wav)", type=["wav"])
    
    if uploaded_file is not None:
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            st.session_state.audio_file = tmp_file.name
        
        st.session_state.recording = False
        
        # 음성을 텍스트로 변환
        st.session_state.text = speech_to_text(st.session_state.audio_file)
        
        # 임시 파일 삭제
        os.unlink(st.session_state.audio_file)
        st.session_state.audio_file = None
        
        st.experimental_rerun()

# 변환된 텍스트 표시
if st.session_state.text:
    st.subheader("변환된 텍스트:")
    st.write(st.session_state.text)
    
    # 텍스트 편집 기능
    edited_text = st.text_area("텍스트 편집:", value=st.session_state.text, height=150)
    if edited_text != st.session_state.text:
        st.session_state.text = edited_text

# Supabase 연결 상태 표시
st.sidebar.title("연결 상태")
if supabase_connected:
    st.sidebar.success("Supabase 연결됨")
else:
    st.sidebar.error("Supabase 연결 안됨")
    st.sidebar.info(".env 파일에 SUPABASE_URL과 SUPABASE_KEY를 설정해주세요.")

# 저장된 메모 목록 (Supabase 연결 시)
if supabase_connected:
    st.sidebar.title("저장된 메모")
    if create_table_if_not_exists():
        try:
            response = supabase.table('voice_memos').select('*').order('created_at', desc=True).execute()
            memos = response.data
            
            if memos:
                for memo in memos:
                    with st.sidebar.expander(f"메모 {memo.get('id', '알 수 없음')}"):
                        st.write(memo.get('content', '내용 없음'))
                        st.caption(f"작성일: {memo.get('created_at', '알 수 없음')[:16].replace('T', ' ')}")
            else:
                st.sidebar.info("저장된 메모가 없습니다.")
        except Exception as e:
            st.sidebar.error(f"메모 로드 중 오류 발생: {str(e)}")
