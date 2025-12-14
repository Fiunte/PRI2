# frontend/Dockerfile

# 1. Build Stage
FROM node:22-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

# Expose port 3000
EXPOSE 3000

# Start command (adjust if using Vite/CRA/Next.js)
CMD ["npm", "run", "dev"]