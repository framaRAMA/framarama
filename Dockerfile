FROM python:3-alpine

WORKDIR /home/framarama
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MAGICK_HOME=/usr

EXPOSE 8800

RUN \
  apk add --no-cache sudo git imagemagick imagemagick-dev && \
  pip install --upgrade pip && \
  pip install gunicorn==23.0.0 && \
  mkdir data && \
  mkdir static && \
  chmod ugo+rwx data static

COPY . .

RUN \
  git describe --tags --long > VERSION && \
  git log --pretty='format:%h %aI %d %s' -1 -r $(sed -e 's/.*-g//g' VERSION) >> VERSION && \
  rm -rf .git && \
  pip install -r requirements/default.txt && \
  python manage.py collectstatic --noinput

CMD ["/home/framarama/docs/docker/entrypoint.sh"]

