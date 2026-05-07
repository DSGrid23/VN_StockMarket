import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from data_loader import load_all_tables, load_article
from models.chroma_loader import load_existing_chroma_db
from models.rag_retriever_handler import *
from overview_utils import load_css
    
# Cấu hình trang Streamlit phải là dòng đầu tiên
st.set_page_config(
    page_title="Stock Market Overview",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
def today_news():

    def all_articles():
        formatted = []
        
        for row in df_today.itertuples():
            formatted.append(row.content)
            
        return "\n\n".join(formatted)

    formatted_docs = all_articles()
    query = "Tổng hợp thông tin về thị trường chứng khoán ngày hôm nay"
    if formatted_docs.strip():
        output = rag_chain.invoke({"context": formatted_docs, "question": query})
    else:
        output = rag_chain.invoke({"context": "", "question": query})
            
    # Kiểm tra xem output có dấu '}' ở cuối chuỗi chưa, nếu thiếu thì thêm vào
    if output[-1] != '}':
        output += '}'   
    print(output)
    print("Tổng hợp thông tin về thị trường chứng khoán ngày hôm nay thành công")
    output_json = json.loads(remove_json_formatting(output))
    return output_json['answer']

# Các thành phần
def setup_main_page():
    st.markdown('<h1 class="title">Ứng dụng Phân tích Chứng khoán</h1>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="intro-text">
            Chào mừng bạn đến với ứng dụng phân tích chứng khoán của tôi! 
            Ứng dụng này giúp bạn phân tích và theo dõi sự biến động giá cổ phiếu, 
            cung cấp những chỉ số và biểu đồ hỗ trợ ra quyết định đầu tư hiệu quả.
        </div>
        """, unsafe_allow_html=True
    )

# Tải CSS từ file
load_css("styles/Stock_App.css")

# Gọi hàm thiết lập trang chính
setup_main_page()


if "data_frames" not in st.session_state:
    st.session_state["data_frames"] = load_all_tables()
    # Thông báo khi dữ liệu đã được tải
    st.success("Dữ liệu đã được tải thành công !!!")

if "vector_db" not in st.session_state:
    st.session_state["vector_db"] = load_existing_chroma_db("vector_db")
    st.success("Vector DB đã được tải thành công !!!")
    
if "article" not in st.session_state:
    st.session_state["article"] = load_article()
    st.success("Article đã được tải thành công !!!")

df = st.session_state["article"]
max_date = max(df['date'])
df_today = df[df['date'] == max_date]


# Hiển thị phần tiêu đề Tổng hợp thông tin thị trường chứng khoán
st.markdown('<h2 class="header-market-summary">Tổng hợp thông tin thị trường chứng khoán ngày hôm nay</h2>', unsafe_allow_html=True)

# Hiển thị phần tin tức (news summary)
news_summary = today_news()
st.markdown(f'<div class="news-summary">{news_summary}</div>', unsafe_allow_html=True)

# Hiển thị các bài báo mới nhất
st.header("Các bài báo mới nhất")
for article in df_today.itertuples():
    st.markdown(f'''
        <div class="article-container">
            <a href="{article.link}" class="article-link" target="_blank">
                <h3 class="article-title">🔥 {article.title}</h3>
            </a>
        </div>
    ''', unsafe_allow_html=True)

