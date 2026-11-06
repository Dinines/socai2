FROM socai2-next-api:20261104-n15
WORKDIR /app
COPY --chown=0:10001 app/socai2 /app/app/socai2
COPY --chown=0:10001 app/models/socai2.py /app/app/models/socai2.py
COPY --chown=0:10001 processing_job.py processing_smoke.py /opt/processor/
COPY --chown=0:10001 smoke-fusion /opt/processor/smoke-fusion
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 10001:10001
HEALTHCHECK NONE
ENTRYPOINT ["python", "-B", "/opt/processor/processing_job.py"]
CMD ["--help"]
