FROM node:20-alpine AS construir
# sin aviso de versiones nuevas de npm: esa consulta a la red colgaba el build ~13 min
ENV NPM_CONFIG_UPDATE_NOTIFIER=false NPM_CONFIG_FUND=false NPM_CONFIG_AUDIT=false
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=construir /app/dist /usr/share/nginx/html
EXPOSE 80
