# Gelistirme imaji (compose.dev.yaml): Vite dev server + HMR + polling.
FROM docker.io/library/node:22-alpine AS dev
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

# Uretim derlemesi: yalnizca statik cikti uretir (dist/).
FROM dev AS build
RUN npm run build

# Gunluk (stable) runtime: derlenmis SPA + /api proxy'si. Vite, HMR, dosya
# izleyici ve node process'i YOKTUR -- bkz. compose.yaml / compose.dev.yaml.
FROM docker.io/library/nginx:1.27-alpine AS prod
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Imajin varsayilan index.html'ini once sil: dist uretilemezse eski varsayilan
# sayfa sessizce servis edilmesin.
RUN rm -rf /usr/share/nginx/html
COPY --from=build /app/dist /usr/share/nginx/html
