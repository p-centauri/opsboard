FROM node:24-slim AS base
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app

FROM base AS deps
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# Dev: source bind-mounted by Compose, hot reload.
FROM deps AS dev
COPY . .
CMD ["npm", "run", "dev"]

FROM deps AS build
ARG API_URL
ENV API_URL=$API_URL
COPY . .
RUN npm run build

# Prod: Next standalone output only, non-root.
FROM base AS prod
ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
