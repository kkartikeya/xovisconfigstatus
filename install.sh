#!/bin/bash

# Create /var/www/status directory
mkdir -p /var/www/status

# Copy all the resources to /var/www/status 
cp -r resources /var/www/status/

# Change File permissions for all the files under /var/www/status
chmod -R 755 /var/www/status

# Dump crontab to a file
crontab -l > mycron

# Add config status to the crontab dump file
echo "0 0 * * * cd xovisconfigstatus; python xovisconfigstatus.py" >> mycron

# Add the entire crontab back
crontab mycron

# remove the crontab dump file
rm -rf mycron

# Copy the Apache configuration file to /etc/httpd/conf.d/
cp 1_status.conf /etc/httpd/conf.d/

# Restart the Apache Web Server
/sbin/service httpd restart