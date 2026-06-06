FROM python:3.12-slim
WORKDIR /sandbox
RUN pip install --no-cache-dir numpy pandas scipy sympy qiskit
CMD ["python", "-c", "print('sandbox ready')"]
