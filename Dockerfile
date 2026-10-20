FROM python:3.13-slim
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock && useradd --uid 10001 --create-home range
COPY app.py ./
COPY data ./data
COPY templates ./templates
COPY static ./static
RUN mkdir instance && chown range:range instance
USER 10001
EXPOSE 4891
CMD ["waitress-serve", "--listen=0.0.0.0:4891", "--call", "app:create_app"]
