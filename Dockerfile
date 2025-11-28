FROM python:3.10-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python3", "server.py"]
EXPOSE 8001
EXPOSE 54000 
EXPOSE 1900/udp