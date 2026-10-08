FROM node:20-slim
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (ignoring optional dep errors that might occur on windows builds)
RUN npm install

# Copy application code
COPY . .

# Expose port
EXPOSE 3000

# Run vite dev server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
