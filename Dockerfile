FROM python:3.10-alpine
RUN mkdir /app
WORKDIR /app

ENV PYTHONUNBUFFERED 1
RUN apk add --update --no-cache postgresql-client jpeg-dev
RUN apk add --update --no-cache --virtual .tmp-build-deps \ 
    gcc libc-dev linux-headers postgresql-dev musl-dev zlib zlib-dev
RUN apk del .tmp-build-deps
RUN pip install pipenv

COPY ./ /app

RUN pipenv sync --dev --system


