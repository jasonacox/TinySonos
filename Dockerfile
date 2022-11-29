FROM python:3.10
WORKDIR /app
RUN pip3 install soco
COPY . .
CMD ["python3", "server.py"]
EXPOSE 8001
EXPOSE 54000 
