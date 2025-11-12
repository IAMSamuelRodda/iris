# Use Node.js 21 as the base image for building the application
FROM node:21 AS builder

# Set the working directory in the container for the build stage
WORKDIR /usr/src/app

# Copy package.json and package-lock.json for dependency installation
COPY package*.json ./

# Install dependencies, including those necessary for building the application
RUN npm install --legacy-peer-deps

# Copy the rest of the application source code
COPY . .

# Compile TypeScript to JavaScript
RUN npm run build

# Start a new, final image to reduce size, using Node.js 21 slim variant
FROM node:21-slim

# Create a non-root user for running the application
RUN useradd --create-home appuser

# Set the working directory in the container for the appuser
WORKDIR /home/appuser

# Switch to the non-root user for security
USER appuser

# Ensure the "type": "module" setting is preserved in the final image
# This step is crucial for enabling ES Module support
COPY --from=builder /usr/src/app/package.json ./

# Copy the build artifacts and node_modules from the build stage to the final image
COPY --from=builder /usr/src/app/dist ./dist
COPY --from=builder /usr/src/app/node_modules ./node_modules

# Expose the port on which the application will run
EXPOSE 8080

# Command to run the application
CMD ["node", "dist/index.js"]
