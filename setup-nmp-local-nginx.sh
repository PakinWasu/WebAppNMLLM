#!/bin/bash
# Setup nginx on host for nmp.local domain
# Run this script with sudo

DOMAIN="nmp.local"
NGINX_CONFIG="/etc/nginx/sites-available/mnp"

echo "Setting up nginx for domain: $DOMAIN"

# Create nginx config
sudo tee "$NGINX_CONFIG" > /dev/null <<EOF
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN} _;
    
    # Increase client body size for file uploads
    client_max_body_size 10M;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json application/javascript;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # API proxy - proxy all API endpoints to backend
    location ~ ^/(auth|users|projects|ai|docs|openapi\.json|folders|summary|project-options) {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # Increase timeouts for long-running requests
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        
        # Disable buffering for streaming responses
        proxy_buffering off;
    }
    
    # Frontend static files (proxy to Docker container on port 8080)
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable site
sudo ln -sf "$NGINX_CONFIG" /etc/nginx/sites-enabled/mnp

# Remove default if exists
if [ -f /etc/nginx/sites-enabled/default ]; then
    sudo rm /etc/nginx/sites-enabled/default
fi

# Test and reload
if sudo nginx -t; then
    echo "✓ Nginx configuration is valid"
    sudo systemctl reload nginx
    echo "✓ Nginx reloaded"
    echo ""
    echo "Domain setup complete!"
    echo "Access: http://$DOMAIN"
else
    echo "✗ Nginx configuration has errors"
    exit 1
fi
