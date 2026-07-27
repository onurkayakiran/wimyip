FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py config.py ./

# NOT: diger servislerin aksine bu container ROOT olarak calisir. Sebebi:
# /var/run/docker.sock'a erisimi var (asagida docker-compose.yml'de mount
# ediliyor) ve host'taki socket'in grup sahipligi makineden makineye
# degisebilir (genelde "docker" grubu, gid'i host'a gore farklilasir) -
# ayricaliksiz bir kullanicinin bu gid'i onceden bilip eslesmesi guvenilir
# degil. Bu servis SADECE compose'un internal agindan (token'li) erisilebilir,
# disariya hicbir port acmiyor - riski buradan sinirliyoruz.
EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
