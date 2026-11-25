FROM python:3.12-slim
WORKDIR /app
RUN groupadd -r swarm && useradd -r -g swarm swarm && mkdir /data && chown swarm:swarm /data
COPY server.py strategy.py index.html participate.html join.txt /app/
USER swarm
ENV SWARM_HOST=0.0.0.0 SWARM_DB=/data/swarm.sqlite PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000
VOLUME ["/data"]
CMD ["python","server.py"]
