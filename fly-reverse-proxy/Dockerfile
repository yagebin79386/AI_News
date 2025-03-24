FROM nginx:alpine

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 8084
EXPOSE 8084

# Start nginx
CMD ["nginx", "-g", "daemon off;"] 