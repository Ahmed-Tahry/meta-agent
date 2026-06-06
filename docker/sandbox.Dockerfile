FROM python:3.12-slim
WORKDIR /sandbox
CMD ["python", "-c", "print('sandbox ready')"]
