# Cấu hình Apache Airflow

``` terminal
<!-- Cài đặt cho một chương trình airflow docker -->

docker --version
docker-compose --version
Invoke-WebRequest -Uri 'https://airflow.apache.org/docs/apache-airflow/2.10.2/docker-compose.yaml' -OutFile 'docker-compose.yaml'
```


**Thay đổi môi trường**
``` yaml
    x-airflow-common:
    &airflow-common
    # In order to add custom dependencies or upgrade provider packages you can use your extended image.
    # Comment the image line, place your Dockerfile in the directory where you placed the docker-compose.yaml
    # and uncomment the "build" line below, Then run `docker-compose build` to build the images.
    # image: ${AIRFLOW_IMAGE_NAME:-apache/airflow:2.10.2}
    build: .


  airflow-webserver:
    build:
      context: .  
      dockerfile: Dockerfile 
    env_file:
      - .env
    
  airflow-scheduler:
    build:
      context: .  
      dockerfile: Dockerfile
    env_file:
      - .env


  airflow-worker:
    build:
      context: .  
      dockerfile: Dockerfile 
    env_file:
      - .env
```

**Tạo các thư mục cần thiết cho Apache Airflow**
``` terminal
mkdir -p ./dags, ./logs, ./plugins
```
# Tạo dabase cho Apache Airflow
- Tải extension PosgreSQL cho Apache Airflow
- Sử dung trang [Render](https://dashboard.render.com/) để tạo một database PosgreSQL
- Dán link database vào file .env với tên là `DATABASE_RENDER`
- Sử dụng extentension PostgresSQL tạo 1 connection dán cái link vào từ sau dấu `@` đến hết `.com` trong `DATABASE_RENDER`
- Lấy thông tin trên website để kết nối vào

# Tạo các bảng cho database
- Sử dụng lệnh `python .\create_and_insert_stock_info_table.py` để tạo các bảng cho database
- Tạo bảng create_and_insert_stock_info đầu tiên sau đó mới tạo các bảng khác

# Khởi chạy Apache Airflow
``` terminal
<!-- initialize Apache Airflow with the following command: -->
docker-compose up airflow-init

<!-- start Apache Airflow with the following command: -->
docker-compose up -d

<!-- to check the status of the services -->
docker-compose ps 

<!-- to check the logs of the services -->
docker exec -it [name of container websever] env


<!-- to stop Apache Airflow -->
docker-compose down
``` 