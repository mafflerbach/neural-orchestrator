# frontend/Dockerfile

FROM node:18-alpine
WORKDIR /app

# Copy npm lockfile and manifest, install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy the rest of your code (including tailwind.config.js, postcss.config.js, src/)
COPY . .

EXPOSE 3000

# Start the CRA dev server
CMD ["npm", "start"]
