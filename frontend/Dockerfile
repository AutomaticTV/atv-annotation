FROM alpine:3.11.3 as builder

ARG VUE_APP_BACKEND_URL
ENV VUE_APP_BACKEND_URL=$VUE_APP_BACKEND_URL

WORKDIR /app/
COPY ./ /app

# Frontend dependences
RUN apk update
RUN apk add nodejs npm

RUN npm install && npm run build

FROM nginx:1.18.0-alpine

COPY --from=builder /app/dist/ /usr/share/nginx/html
