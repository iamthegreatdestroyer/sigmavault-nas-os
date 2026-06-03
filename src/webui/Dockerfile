FROM node:20-alpine

WORKDIR /app

# Use npm for reliable flat node_modules in Docker
COPY package.json ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
