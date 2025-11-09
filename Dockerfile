# ---------------------------------------------------------
# Global ARGs（放在所有 FROM 之前，可被后续 stage 继承）
# ---------------------------------------------------------
ARG APT_MIRROR="mirrors.ustc.edu.cn"
#ARG PIP_INDEX_URL="https://bkrepo.cwoa.net/pypi/aiops/kingeye-pypi/simple"


# ---------------------------------------------------------
# Build 后端公共部分
# ---------------------------------------------------------
FROM python:3.11.12-slim-bullseye AS backend-buildbase
ARG APT_MIRROR
#ARG PIP_INDEX_URL

USER root
# 修复 sed 命令，使用正确的分隔符避免 URL 中的斜杠干扰
RUN sed -i "s/deb.debian.org/${APT_MIRROR}/g" /etc/apt/sources.list && \
    sed -i "s/security.debian.org/${APT_MIRROR}/g" /etc/apt/sources.list
# 缓存 apt-get 下载的包，提升构建速度 apt需要锁定缓存
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
  apt-get update && apt-get install -y gcc ssh default-libmysqlclient-dev pkg-config vim git gettext libjpeg-dev zlib1g-dev wget

#RUN mkdir ~/.pip && printf '[global]\nindex-url = ${PIP_INDEX_URL}\n' > ~/.pip/pip.conf

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade 'pip'
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install uv

# Change security level of openssl to lower value in order to avoid "CA_MD_TOO_WEAK" error
# See https://stackoverflow.com/questions/52218876/how-to-fix-ssl-issue-ssl-ctx-use-certificate-ca-md-too-weak-on-python-zeep?rq=1
RUN sed -i "s/DEFAULT@SECLEVEL=2/DEFAULT@SECLEVEL=0/g" /etc/ssl/openssl.cnf


WORKDIR /app

# Final stage
FROM backend-buildbase as backend-production

# Set working directory
WORKDIR /app

ADD . .
# Install dependecies in system, ignore dev dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --all-extras

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings

# Create log directories
RUN mkdir -p /var/log/supervisor && \
    chmod -R 755 /var/log/supervisor

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose port
EXPOSE 8000

# Run entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
