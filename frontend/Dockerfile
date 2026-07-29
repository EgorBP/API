FROM node:22-alpine AS build

WORKDIR /app

ARG VITE_API_BASE_URL=/api
ARG VITE_MEDIA_BASE_URL=
ARG VITE_DEV_MODE=false
ARG VITE_DEV_AUTH_ENDPOINT=/v1/dev/auth/{tg_user_id}
ARG VITE_TELEGRAM_BOT_USERNAME=

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_MEDIA_BASE_URL=$VITE_MEDIA_BASE_URL
ENV VITE_DEV_MODE=$VITE_DEV_MODE
ENV VITE_DEV_AUTH_ENDPOINT=$VITE_DEV_AUTH_ENDPOINT
ENV VITE_TELEGRAM_BOT_USERNAME=$VITE_TELEGRAM_BOT_USERNAME

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
