FROM public.ecr.aws/lambda/python:3.12
COPY app/ ${LAMBDA_TASK_ROOT}/app/
CMD ["app.handler.handler"]
