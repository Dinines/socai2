ARG BASE_IMAGE
FROM ${BASE_IMAGE}
ARG RUNTIME_USER
WORKDIR /app
USER 0:0
# Replace the application snapshot; removed base-image modules must not survive.
RUN rm -rf /app/app /opt/processor
COPY --chown=${RUNTIME_USER} app /app/app
COPY --chown=${RUNTIME_USER} processing_job.py production_ingress.py manifest.json investigation-policy.toml /opt/processor/
COPY --chown=${RUNTIME_USER} smoke-fusion /opt/processor/smoke-fusion
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER ${RUNTIME_USER}
HEALTHCHECK NONE
ENTRYPOINT ["python", "-B", "/opt/processor/processing_job.py"]
CMD ["--help"]
