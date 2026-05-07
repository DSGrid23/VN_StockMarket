import json
import os
import re
from dotenv import load_dotenv
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain.schema import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableMap, RunnablePassthrough
from langchain_openai import ChatOpenAI
import logging
from datetime import date, datetime, timedelta
from models.chroma_loader import load_existing_chroma_db

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

############### NER with LLM ###############
llm_ner = ChatOpenAI(
    temperature=1,
    streaming=True,
    model="gpt-4o-mini",
    openai_api_key=openai_api_key,
)

system_ner = """
You are an expert in Named Entity Recognition (NER). 
Your task is to extract all dates mentioned in the query. 
Ensure all dates are formatted as DD/MM/YYYY.
Additionally, extract all NER entities from the query. 
"""

# Định nghĩa prompt để trích xuất ngày
prompt_date_extraction = """
    Tách tất cả ngày tháng được đề cập trong câu truy vấn "{query}". 
    Hôm nay là {today}. Tôi cung cấp thông tin này để bạn hiểu ngữ cảnh về thời gian đang được đề cập đến trong câu hỏi.

    - Nếu người dùng đề cập đến các thời điểm như "hôm nay", "ngày mai", "hôm qua", "tháng này", "năm nay", v.v., hãy suy luận và trích xuất các ngày tương ứng với thời điểm đó.
    - Nếu người dùng đề cập đến một khoảng thời gian cụ thể từ đâu tới đâu, hãy liệt kê tất cả các ngày trong khoảng thời gian đó.
    - Nếu câu hỏi không có liên quan đến {today} thì đừng trả về {today} trong kết quả.
    
    Trả về kết quả dưới phải định dạng chi tiết theo JSON như sau:
    {{
        'dates': Danh sách các ngày được tìm thấy trong câu truy vấn, định dạng DD/MM/YYYY. Nếu là khoảng thời gian, trả về tất cả các ngày trong khoảng đó (ví dụ: "từ ngày DD/MM/YYYY đến DD/MM/YYYY"). Nếu không tìm thấy ngày nào, trả về [].
        'months': Danh sách các tháng được tìm thấy trong câu truy vấn, định dạng MM/YYYY. Nếu không tìm thấy, trả về []
        'years': Danh sách các năm được tìm thấy trong câu truy vấn, định dạng YYYY. Nếu không tìm thấy, trả về []
        'entities': Danh sách các vật thể (Named Entities) được tìm thấy trong câu truy vấn, ví dụ: tên người, địa điểm, tổ chức, v.v. Nếu không tìm thấy, trả về [].
    }}
    
"""


# Tạo template cho prompt
date_extraction_prompt = ChatPromptTemplate.from_messages(
    [("system", system_ner), ("human", prompt_date_extraction)]
)

def remove_json_formatting(input_text):
    # Loại bỏ dấu ```json và ``` nếu chúng có trong input_text
    cleaned_text = input_text.strip("```json").strip("```").strip()
    return cleaned_text

def extract_date_and_entities(query):
    # Lấy ngày hiện tại
    today_date = date.today().strftime("%d/%m/%Y")
    
    prompt = date_extraction_prompt.format(query=query, today=today_date)
    response = llm_ner.invoke(prompt)
    # print(response.content)
    result = json.loads(remove_json_formatting(response.content))
    return result


############### RAG Retriever ###############
llm = ChatOpenAI(
    temperature=0.2,
    streaming=True,
    model="gpt-4o-mini",
    max_tokens=500,
    openai_api_key=openai_api_key,
)

system = """
Bạn là một chuyên gia chứng khoán có tên là StockAI, với nhiều năm kinh nghiệm phân tích thị trường chứng khoán và các chiến lược đầu tư. 
Dưới đây là thông tin bạn cần tham khảo để trả lời câu hỏi từ người dùng:
{context}

Câu trả lời của bạn phải được viết bằng tiếng Việt và phải theo định dạng JSON như sau:
{{
    "question": "Câu hỏi của người dùng",
    "answer": "Câu trả lời của bạn"
}}

Yêu cầu:
1. Tổng hợp thông tin liên quan đến câu hỏi trong các tài liệu được cung cấp cho bạn, bạn không cần đưa ra dẫn chứng. 
2. Nếu tài liệu không liên quan đến câu hỏi hoặc không cung cấp thông tin đủ, bạn phải trả lời bằng câu: "Chúng tôi không tìm thấy thông tin liên quan."
4. Hãy đảm bảo câu trả lời rõ ràng, chính xác, và dễ hiểu.

Lưu ý:
- Nếu không có tài liệu hoặc thông tin liên quan, bạn cần trả lời một cách trung thực và rõ ràng, không tạo ra các giả định không có căn cứ.
"""



prompt_template = ChatPromptTemplate.from_messages(
    [("system", system), ("human", "Question: {question}")]
)

# Khởi tạo chuỗi RAG với prompt_template
rag_chain = (
    RunnableMap(
        {"context": RunnablePassthrough(), "question": RunnablePassthrough()}
    )
    | prompt_template
    | llm
    | StrOutputParser()
)

def find_condition_date(time):
    # Lấy các giá trị từ time
    dates = time.get("dates")
    months = time.get("months")
    years = time.get("years")
    
    # Hàm để tạo danh sách ngày từ tháng (MM/YYYY)
    def generate_dates_from_month(month_str):
        try:
            month_date = datetime.strptime(month_str, "%m/%Y")
            # Tính toán số ngày trong tháng
            first_day = month_date.replace(day=1)
            next_month = first_day.replace(month=first_day.month % 12 + 1)
            last_day_of_month = next_month - timedelta(days=1)
            
            # Tạo danh sách tất cả các ngày trong tháng
            days_in_month = [first_day + timedelta(days=i) for i in range((last_day_of_month - first_day).days + 1)]
            return [day.strftime("%d/%m/%Y") for day in days_in_month]
        except ValueError:
            return []

    # Hàm để tạo danh sách ngày từ năm (YYYY)
    def generate_dates_from_year(year_str):
        try:
            year_date = datetime.strptime(year_str, "%Y")
            # Tạo danh sách tất cả các ngày trong năm
            first_day_of_year = year_date.replace(month=1, day=1)
            last_day_of_year = year_date.replace(month=12, day=31)
            
            # Tạo danh sách tất cả các ngày trong năm
            days_in_year = [first_day_of_year + timedelta(days=i) for i in range((last_day_of_year - first_day_of_year).days + 1)]
            return [day.strftime("%d/%m/%Y") for day in days_in_year]
        except ValueError:
            return []

    # Điều kiện lọc dựa trên ngày, tháng, năm
    filter_conditions = None

    if len(dates) > 0: 
        filter_conditions = {"date": dates}
    elif len(months) > 0:
        # Chuyển đổi tháng thành tất cả các ngày trong tháng
        all_dates_from_months = []
        for month in months:
            all_dates_from_months.extend(generate_dates_from_month(month))
        filter_conditions = {"date": all_dates_from_months}
    elif len(years) > 0:
        # Chuyển đổi năm thành tất cả các ngày trong năm
        all_dates_from_years = []
        for year in years:
            all_dates_from_years.extend(generate_dates_from_year(year))
        filter_conditions = {"date": all_dates_from_years}
    
    if filter_conditions is None:
        return None
    
    filter_dict = {'date': {'$in': filter_conditions['date']}}
    return filter_dict

# Hàm định dạng tài liệu thành chuỗi và lấy link và title từ metadata
def format_docs(docs):
    formatted_docs = []
    
    unique_pairs = set()
    links = []
    titles = []

    # Duyệt qua các tài liệu và thêm link, title vào list nếu chưa tồn tại trong set
    for doc in docs:
        formatted_docs.append(doc.page_content)
        
        if 'link' in doc.metadata and 'title' in doc.metadata:
            link = doc.metadata['link']
            title = doc.metadata['title']
        
            if (link, title) not in unique_pairs:
                unique_pairs.add((link, title))
                links.append(link)
                titles.append(title)
    return "\n\n".join(formatted_docs), links, titles

def create_retriever(vector_db, query):
    # Tạo điều kiện lọc dựa vào ngày tháng
    time = extract_date_and_entities(query)
    entities = time.get("entities")
    filter_conditions = find_condition_date(time)
    print("Creating retriever.....!")

    # Cấu hình search_kwargs mặc định
    search_kwargs = {"k": 100}
    if filter_conditions is not None:
        search_kwargs["filter"] = filter_conditions

    # Tạo chroma retriever với điều kiện lọc
    chroma_retriever = vector_db.as_retriever(
        search_type="similarity", search_kwargs=search_kwargs
    )
    print("Done chroma retriever!")

    # Kết hợp retriever (chroma) thành ensemble retriever
    ensemble_retriever = EnsembleRetriever(
        retrievers=[chroma_retriever], weights=[1.0]
    )

    print("Retriever created!")
    return ensemble_retriever, filter_conditions



# Hàm lấy tài liệu phù hợp từ retriever
def retrieve_documents(ensemble_retriever, query, top_k):
    print("Retrieving documents.....!")
    docs = ensemble_retriever.invoke(query)
    print(f"Found {len(docs)} relevant documents")
    
    return docs[:min(top_k, len(docs))]


# Hàm xử lý truy vấn và trả về tài liệu
def rag_retriever_handler(vector_db, query, top_k = 5):
    print(f"Rag retriever handler...: {query}")
    
    ensemble_retriever, filter_conditions = create_retriever(vector_db, query)
    print(filter_conditions)
    
    
    # Lấy những tài liệu liên quan
    docs = ensemble_retriever.invoke(query)
    print(f"Found {len(docs)} relevant documents")
    docs = docs[:min(top_k, len(docs))]
    # docs = retrieve_documents(ensemble_retriever, query, top_k=top_k)
    
    
    print("Fotmatting docs.....!")
    # Định dạng tài liệu và lấy link, title
    formatted_docs, links, titles = format_docs(docs)

    if formatted_docs.strip():
        output = rag_chain.invoke({"context": formatted_docs, "question": query})
    else:
        output = rag_chain.invoke({"context": "", "question": query})
        
    # Kiểm tra xem output có dấu '}' ở cuối chuỗi chưa, nếu thiếu thì thêm vào
    if output[-1] != '}':
        output += '}'   
    print(output)
    print("Rag retriever handler done!!!")
    output_json = json.loads(remove_json_formatting(output))
    print(output_json)
    output_json['links'] = links
    output_json['titles'] = titles
    return output_json
