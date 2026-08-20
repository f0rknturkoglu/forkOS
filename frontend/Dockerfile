FROM docker.io/library/node:22-alpine
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
