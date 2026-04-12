# Multi-stage build for GotJUNK? FoundUp
# Stage 1: Build the Vite app
FROM node:20-alpine AS builder

WORKDIR /app

# Build-time arguments for Vite environment variables
ARG VITE_FIREBASE_API_KEY
ARG VITE_FIREBASE_APP_ID
ARG VITE_FIREBASE_SENDER_ID

# Set as environment variables for Vite build
ENV VITE_FIREBASE_API_KEY=$VITE_FIREBASE_API_KEY
ENV VITE_FIREBASE_APP_ID=$VITE_FIREBASE_APP_ID
ENV VITE_FIREBASE_SENDER_ID=$VITE_FIREBASE_SENDER_ID

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build for production (Vite embeds VITE_* vars at build time)
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration for SPA routing
# WSP 104: Allow shell embedding via frame-ancestors (replaces X-Frame-Options)
RUN echo 'server { \
    listen 8080; \
    server_name _; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
    # Enable CORS for IPFS \
    add_header Access-Control-Allow-Origin *; \
    # Security headers - WSP 104 shell embedding \
    add_header Content-Security-Policy "frame-ancestors https://*.foundups.com https://foundups.com https://*.web.app https://*.firebaseapp.com http://localhost:* https://localhost:*" always; \
    add_header X-Content-Type-Options "nosniff" always; \
    add_header X-XSS-Protection "1; mode=block" always; \
    # Cache static assets \
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ { \
        expires 1y; \
        add_header Cache-Control "public, immutable"; \
    } \
}' > /etc/nginx/conf.d/default.conf

# Expose Cloud Run default port
EXPOSE 8080

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
