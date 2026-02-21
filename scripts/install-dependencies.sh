#!/bin/bash
# Install Frappe dependencies on Ubuntu 22.04/24.04
# Run with: sudo bash scripts/install-dependencies.sh

set -e

echo "Installing Frappe Framework dependencies..."

# Update system
sudo apt-get update -y
sudo apt-get upgrade -y

# Python
sudo apt-get install -y python3-dev python3-pip python3-venv python3-setuptools

# MariaDB
sudo apt-get install -y mariadb-server mariadb-client libmysqlclient-dev

# Redis
sudo apt-get install -y redis-server

# Node.js 18 (via NodeSource)
if ! command -v node &> /dev/null || [[ $(node -v | cut -d. -f1 | tr -d v) -lt 18 ]]; then
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# Yarn
sudo npm install -g yarn

# wkhtmltopdf (for PDF generation)
sudo apt-get install -y xvfb libfontconfig wkhtmltopdf

# Other dependencies
sudo apt-get install -y \
    git \
    nginx \
    supervisor \
    cron \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    libxml2-dev \
    libxslt1-dev

# Configure MariaDB
echo "Configuring MariaDB..."
sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED BY 'your_root_password';" 2>/dev/null || true

# Add Frappe-required MariaDB config
sudo tee /etc/mysql/mariadb.conf.d/99-frappe.cnf > /dev/null << 'EOF'
[mysqld]
character-set-client-handshake = FALSE
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

[mysql]
default-character-set = utf8mb4
EOF

sudo systemctl restart mariadb
sudo systemctl enable mariadb
sudo systemctl enable redis-server

# Install bench
pip3 install frappe-bench --break-system-packages

echo ""
echo "============================================"
echo "Dependencies installed!"
echo ""
echo "Next steps:"
echo "  bench init --frappe-branch version-15 uw-bench"
echo "  cd uw-bench"
echo "  bench new-site uw.localhost --mariadb-root-password your_root_password --admin-password admin"
echo "  ln -s $(pwd)/../united_way apps/united_way"
echo "  bench --site uw.localhost install-app united_way"
echo "  bench start"
echo "============================================"
