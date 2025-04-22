FROM node:20-alpine as build

WORKDIR /app

# Install dependencies
COPY package.json package-lock.* ./
RUN npm install

# Build the application
COPY . .
RUN npm run build

# ====================================
FROM node:20-alpine as release

WORKDIR /app

# Install serve globally
RUN npm install -g serve

# Copy built files from previous stage
COPY --from=build /app/out /app/out

# Expose port
EXPOSE 3000

# Serve the application
CMD ["serve", "-s", "out", "-l", "3000"]
