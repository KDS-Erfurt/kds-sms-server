FROM python:3.13-bookworm

LABEL title = "KDS SMS Server"
LABEL description = "A broker server for sending SMS."
LABEL version = "3.1.0"
LABEL author = "Kirchhoff Datensysteme Services GmbH & Co. KG - Julius Koenig"
LABEL author_email = "julius.koenig@kds-kg.de"
LABEL license = "GPL-3.0"

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