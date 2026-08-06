FROM ghcr.io/openclaw/openclaw:latest

# Switch to root to install plugin dependencies
USER root

# Setup build-x-claw plugin
RUN mkdir -p /home/node/.openclaw/extensions/build-x-claw
COPY build-x-claw/ /home/node/.openclaw/extensions/build-x-claw/
RUN cd /home/node/.openclaw/extensions/build-x-claw && npm install --production
RUN chown -R node:node /home/node/.openclaw

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch back to non-root user
USER node

# Expose build-x-claw HTTP server port and OpenClaw gateway port
EXPOSE 18788
EXPOSE 18789

# Environment variables with defaults
ENV CLAW_TTL_SECONDS=0
ENV CLAW_SHUTDOWN_GRACE_SECONDS=30
ENV BUILD_X_API_BASE_URL=""
ENV BUILD_X_API_KEY=""
ENV OPENCLAW_GATEWAY_TOKEN=""

ENTRYPOINT ["/entrypoint.sh"]
