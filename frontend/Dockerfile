# syntax=docker/dockerfile:1
# Stage 1: install production dependencies only
FROM node:20-alpine AS builder
WORKDIR /build
COPY package.json .
RUN npm install --omit=dev

# Stage 2: lean runtime image
FROM node:20-alpine
RUN addgroup -S appgroup && adduser -S -u 1001 appuser -G appgroup
WORKDIR /app
COPY --from=builder /build/node_modules ./node_modules
COPY app.js .
COPY views ./views
USER appuser
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node -e \
    "const h=require('http');h.get('http://localhost:3000/health',r=>{process.exit(r.statusCode===200?0:1)}).on('error',()=>process.exit(1))"
CMD ["node", "app.js"]
