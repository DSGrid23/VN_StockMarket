# Chạy chương trình dashboard

## 1 Cài đặt

- **Embeding dữ liệu**

  - Cần phải có file `article.csv` chứa dữ liệu bó (table to csv ở bảng `article` trong database)
  - Chạy script để embeding dữ liệu
  ```bash
  python ./models/chroma_loader.py ./data/article.csv vector_db
  ```

- **Thêm key openai vào file `.env`**
```bash

OPENAI_API_KEY=sk-...
```

- **Khởi chạy dashboard**
```bash
streamlit run Stock_App.py
```



