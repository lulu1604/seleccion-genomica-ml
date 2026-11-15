FROM python:3.12-slim
WORKDIR /srv
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
COPY dashboard/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
ENV U2NET_HOME=/srv/pesos/u2net TORCH_HOME=/srv/pesos/torch \
    PYTHONPATH=/srv BOVIGEN_RAIZ=/datos
# descarga los pesos al construir (no en cada arranque)
RUN python -c "from rembg import new_session; new_session('u2net')" \
 && python -c "from torchvision import models; models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)"
COPY src ./src
COPY dashboard/backend/app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
