# Minimal image: no third-party runtime deps, CLI as entrypoint.
FROM python:3.12-slim AS base

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .

# Run as non-root.
RUN useradd --create-home --uid 10001 tabayyan
USER tabayyan

ENTRYPOINT ["tabayyan"]
CMD ["--help"]
