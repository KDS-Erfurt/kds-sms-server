FROM python:3.11-bookworm

RUN pip install --upgrade pip
WORKDIR /opt/kds-sms-server
COPY ./src ./src
COPY ./tests ./tests
COPY ./pyproject.toml ./pyproject.toml
COPY ./README.md ./README.md
COPY ./LICENSE ./LICENSE
RUN python3 -m venv ./
RUN ./bin/pip install -e .
RUN ln ./bin/kds-sms-server /usr/bin/kds-sms-server