FROM debian:bullseye-slim

LABEL maintainer="Franck FERMAN <contact@franckferman.fr>" \
      description="Unleash Metadata Intelligence with MetaDetective." \
      metadetective_version="1.0.9" \
      docker_image_version="1.0.2"

# Install dependencies: Python, pip, exiftool, etc.
RUN apt-get update && \
    apt-get install -y \
        python3 \
        python3-pip \
        libimage-exiftool-perl \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Copy local MetaDetective source code into /app
WORKDIR /app
COPY . /app

# Install MetaDetective from local source
# Also install cloudscraper from PyPI
RUN ls
RUN pip3 install --no-cache-dir . \
    && pip3 install --no-cache-dir cloudscraper

# Ensure scripts installed by pip are on PATH
ENV PATH="/root/.local/bin:${PATH}"

# (Optional) keep container running by default (useful for debug)
CMD ["tail", "-f", "/dev/null"]
