FROM ghcr.io/astral-sh/uv:python3.13-alpine

RUN mkdir /app
RUN mkdir /config
WORKDIR /app

# COPY requirements-web.txt .
# RUN pip install -r requirements-web.txt

COPY . .
COPY web.env .

RUN uv sync --locked --no-dev

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "pygrader-web.py", "--server.port=8501", "--server.address=0.0.0.0"]
