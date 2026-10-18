# nginx serving the Vite build and proxying /api/ to the API (ADR 0004 §4). Build from the
# repository root: docker build -f frontend/Dockerfile -t dmc-frontend .
FROM node:24-slim AS build
RUN npm install -g pnpm@12
WORKDIR /srv

COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml frontend/.pnpmfile.cjs frontend/
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    cd frontend && pnpm install --frozen-lockfile

# The bundle embeds the hash of this contract (ADR 0008).
COPY contracts contracts
COPY frontend frontend
RUN cd frontend && pnpm build

FROM nginx:1.29-alpine
# The official image renders /etc/nginx/templates/*.template with envsubst at start-up, and runs
# the scripts in /docker-entrypoint.d, which is how /config.json is written from the environment.
COPY infra/web/default.conf.template /etc/nginx/templates/default.conf.template
COPY infra/web/40-config-json.sh /docker-entrypoint.d/40-config-json.sh
RUN chmod +x /docker-entrypoint.d/40-config-json.sh
COPY --from=build /srv/frontend/dist /usr/share/nginx/html

ENV DMC_API_UPSTREAM=http://api:8000 \
    DMC_API_BASE_URL=
EXPOSE 80
