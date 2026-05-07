import json
import os
import streamlit as st
from langchain_community.callbacks.streamlit import StreamlitCallbackHandler
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
import logging
from models.chroma_loader import load_existing_chroma_db
from models.rag_retriever_handler import rag_retriever_handler
import warnings
warnings.filterwarnings("ignore")

    
# Thiết lập trang Streamlit
def setup_page():
    st.set_page_config(
        page_title="StockAI - Chatbot",
        page_icon="🤖",
        layout="wide",
    )
    # Thiết lập tiêu đề ứng dụng
    st.markdown('<h1 class="title">StockAI - Tư vấn Chứng khoán</h1>', unsafe_allow_html=True)

    
# Cấu hình trang
setup_page()
# Tải file CSS với encoding UTF-8
with open("styles/Chatbot.css", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


if "vector_db" not in st.session_state:
    try:
        st.session_state["vector_db"] = load_existing_chroma_db('vector_db')
        st.success("Vector DB loaded successfully!")
    except Exception as e:
        st.error(f"Không thể tải Vector DB: {e}")
        logging.error(f"Error loading vector DB: {e}")

vector_db = st.session_state.get("vector_db")



def format_output(ret):
    answer = f'<div class="chat-output"><p class="answer">{ret["answer"]}</p>'
    answer += '<div class="references"><strong>Trích dẫn tham khảo:</strong>'
    for title, link in zip(ret["titles"], ret["links"]):
        answer += f'<br><a href="{link}" target="_blank">{title}</a>'
    answer += '</div></div>'
    return answer


# Hàm xử lý câu hỏi và lưu vào lịch sử
def process_question(prompt, msgs, vector_db):
    msgs.add_user_message(f"<div class='user-message'>{prompt}</div>")
    try:
        # Retrieve results from the vector database
        result = rag_retriever_handler(vector_db, prompt, top_k=5)
        logging.info(f"Successfully received answer: {result}")
        
        if result:
            answer_text = format_output(result)
            if answer_text:
                # Add the AI response to chat history and display
                msgs.add_ai_message(answer_text)
                st.markdown(answer_text, unsafe_allow_html=True)
        else:
            st.error("No relevant information found.")
    except Exception as e:
        logging.error(f"Error during question processing: {e}")
        st.error("An error occurred while processing your question. Please try again.")




# Khởi tạo lịch sử trò chuyện
msgs = StreamlitChatMessageHistory(key="chat_messages")

if len(msgs.messages) == 0:
    msgs.add_ai_message("Tôi là trợ lý ảo của bạn. Hãy hỏi tôi về chứng khoán.")

# Hiển thị lịch sử trò chuyện hiện tại
for msg in msgs.messages:
    st.chat_message(msg.type).markdown(msg.content, unsafe_allow_html=True)

# Phần nhập câu hỏi
if prompt := st.chat_input():
    st.chat_message("human").markdown(f"<div class='user-message'>{prompt}</div>", unsafe_allow_html=True)
    with st.spinner("Đang xử lý câu hỏi..."):
        process_question(prompt, msgs, vector_db)

# Hiển thị các tin nhắn mới nhất ngay lập tức
with st.container():
    st.markdown("<div class='input-container'>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)