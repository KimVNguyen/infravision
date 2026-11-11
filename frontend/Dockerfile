FROM node:22-alpine

WORKDIR /app

# Ensure non-root ownership for node user (UID 1000)
RUN chown -R node:node /app

USER node

COPY --chown=node:node package.json package-lock.json ./
RUN npm ci

COPY --chown=node:node entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

COPY --chown=node:node . ./

EXPOSE 5173

ENTRYPOINT ["/app/entrypoint.sh"]
