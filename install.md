#!/bin/bash

# Create Xovis config database
/usr/bin/psql -Upostgres -f CreateDatabase.sql

# Install Python 2.7
apt install python

# Install python postgres package
/usr/local/bin/pip install psycopg2
/usr/local/bin/pip install python-dateutil
/usr/local/bin/pip install requests

# Create /var/www/status directory
mkdir -p /var/www/status

# Copy all the resources to /var/www/status
cp -r resources /var/www/status/

# Change File permissions for all the files under /var/www/status
chmod -R 755 /var/www/status

# Dump crontab to a file
crontab -l > mycron

# Add config status to the crontab dump file
echo "0 03,06,09,12,15,18,21 * * * cd /opt/xovisconfigstatus; python xoviscameralist.py" >> mycron
echo "30 01,04,07,10,13,16,19,22 * * * cd /opt/xovisconfigstatus; python xoviscamconfig.py" >> mycron
echo "*/30 * * * * cd /opt/xovisconfigstatus; python xovisconfigstatus.py" >> mycron

# Add the entire crontab back
crontab mycron

# remove the crontab dump file
rm -rf mycron


#Install apache web server
apt install apache2

# Update port on which apache web server should be listening to. For example change Listen 80 also disable port 443
vim /etc/apache2/ports.conf
# Not sure if this is required. Update the ports in the following file:
vim /etc/apache2/sites-available/000-default.conf

# Enable ProxyPass
a2enmod proxy_http

# Copy the Apache configuration file to /etc/httpd/conf.d/
#cp 1_status.conf /etc/httpd/conf.d/
cp 1_status.conf /etc/apache2/sites-enabled/

mkdir -p /opt/xovis/status/
cp xovis_ibex.properties /opt/xovis/status/

# Update the properties file /opt/xovis/status/xovis_ibex.properties

user=`cat /opt/xovis/status/xovis_ibex.properties | grep 'webgui.user' | cut -f2 -d'=' | tr -d [:space:]`
passwd=`cat /opt/xovis/status/xovis_ibex.properties | grep 'webgui.passwd' | cut -f2 -d'=' | tr -d [:space:]`
/usr/bin/htpasswd -cdb /var/www/status/.htpasswd ${user} ${passwd}

# Restart the Apache Web Server
#/sbin/service httpd restart
/usr/sbin/service apache2 restart
/usr/sbin/service apache2 restart
