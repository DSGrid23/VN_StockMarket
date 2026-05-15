import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from data_loader import load_all_tables, load_article
#from models.chroma_loader import load_existing_chroma_db
#from models.rag_retriever_handler import *
from overview_utils import load_css
from data_loader import load_all_tables
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine
from models.lstm_model import train_shared_model, predict_stock
    
load_dotenv()
conn_str = os.getenv('DATABASE_RENDER')


# Cấu hình trang Streamlit phải là dòng đầu tiên
st.set_page_config(
    page_title="Stock Market Overview",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

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


    
import json

# =========================================
# GET STOCK DATA
# =========================================

stock_data = st.session_state["data_frames"]["stock_data"]

stock_data["trade_date"] = pd.to_datetime(
    stock_data["trade_date"]
)

latest_data_date = str(
    stock_data["trade_date"].max().date()
)

# =========================================
# METADATA PATH
# =========================================

METADATA_PATH = "models/metadata.json"

need_train = True

# =========================================
# CHECK METADATA
# =========================================

if os.path.exists(METADATA_PATH):

    try:

        with open(METADATA_PATH, "r") as f:

            metadata = json.load(f)

        model_last_date = metadata.get(
            "last_train_date"
        )

        # =================================
        # COMPARE DATE
        # =================================

        if model_last_date == latest_data_date:

            need_train = False

            st.success(
                f"""
                Model already updated.

                Latest train date:
                {model_last_date}
                """
            )

        else:

            st.warning(
                f"""
                New data detected.

                Model:
                {model_last_date}

                Data:
                {latest_data_date}

                Retraining model...
                """
            )

            train_shared_model(
                stock_data
            )

    except Exception as e:

        st.error(
            f"""
            Failed to read metadata.

            Error:
            {e}

            Retraining model...
            """
        )

        train_shared_model(
            stock_data
        )

else:

    st.warning(
        "Metadata not found. Training new model..."
    )

    train_shared_model(
        stock_data
    )
