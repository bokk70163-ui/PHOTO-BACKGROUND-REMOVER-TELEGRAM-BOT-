FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

# নিচের লাইনটি খুব গুরুত্বপূর্ণ। এখানে uvicorn worker ব্যবহার করা হয়েছে।
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:10000", "main:server"]
