FROM python:3.10.12

# Create non-root group and user
RUN addgroup --system shared1 \
    && adduser --system --home /var/cache/shared1 --ingroup shared1 --uid 1001 dashuser

WORKDIR /usr/share/shared1/dashapp

COPY requirements.txt /usr/share/shared1/dashapp/

# Elegantly activating a venv in Dockerfile
ENV VIRTUAL_ENV=/usr/share/shared1/dashapp/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install requirements
RUN pip install --trusted-host pypi.python.org -r requirements.txt

COPY . /usr/share/shared1/dashapp/

# set enviroment variables
# This prevent Python from writing out pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# This keeps Python from buffering stdin/stdout
ENV PYTHONUNBUFFERED=1

ENV ENV_FILE=".env"

EXPOSE 7000

USER dashuser

ENTRYPOINT ["gunicorn", "index:server", "-b", "0.0.0.0:7000", "--workers=4"]
