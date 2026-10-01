# syntax=docker/dockerfile:1
FROM node:22.23.2-alpine AS build
WORKDIR /src
COPY package.json package-lock.json .npmrc ./
# exact lockfile, no dependency install scripts
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY . .
RUN npm run build

# nginx-unprivileged runs as UID 101 and listens on 8080, no root needed.
FROM nginxinc/nginx-unprivileged:1.30.5-alpine
USER root
RUN apk upgrade --no-cache
USER 101
# The template is rendered at start-up (envsubst) with AUTH_ORIGIN, so the Content-Security-Policy
# names exactly this environment's Keycloak.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /src/dist /usr/share/nginx/html
EXPOSE 8080
