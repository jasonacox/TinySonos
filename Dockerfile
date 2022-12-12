FROM python:3.10-alpine
WORKDIR /app
RUN pip3 install soco rangehttpserver
COPY . .
CMD ["python3", "server.py"]
EXPOSE 8001
EXPOSE 54000 
