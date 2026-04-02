# Lumens AI Design Consultant Demo - Frontend
# Serves static HTML with embedded AI avatar
FROM nginx:alpine

# Copy nginx configuration
COPY nginx-cloudrun.conf /etc/nginx/nginx.conf

# Copy static files
COPY index.html /usr/share/nginx/html/index.html
COPY lumens-bg.png /usr/share/nginx/html/lumens-bg.png
COPY sdk/ /usr/share/nginx/html/sdk/
COPY data/ /usr/share/nginx/html/data/

# Expose port 8080 for Azure Container Apps
EXPOSE 8080

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
