#!/bin/bash

# Create Xovis config database
/usr/bin/psql -Upostgres -f CreateDatabase.sql

# Upgrade pip
pip install --upgrade pip

# Install python postgres package
/usr/local/bin/pip install psycopg2

# Create /var/www/status directory
mkdir -p /var/www/status

# Copy all the resources to /var/www/status
cp -r resources /var/www/status/

# Change File permissions for all the files under /var/www/status
chmod -R 755 /var/www/status

# Dump crontab to a file
crontab -l > mycron

# Add config status to the crontab dump file
echo "0,15,30,45 * * * * cd /opt/xovisconfigstatus; python xoviscameralist.py" >> mycron
echo "6,21,36,51 * * * * cd /opt/xovisconfigstatus; python xoviscamconfig.py" >> mycron
echo "*/5 * * * * cd /opt/xovisconfigstatus; python xovisconfigstatus.py" >> mycron

# Add the entire crontab back
crontab mycron

# remove the crontab dump file
rm -rf mycron

# Copy the Apache configuration file to /etc/httpd/conf.d/
#cp 1_status.conf /etc/httpd/conf.d/
cp 1_status.conf /etc/apache2/sites-enabled/

mkdir -p /opt/xovis/status/
cp xovis_ibex.properties /opt/xovis/status/

user=`cat /opt/xovis/status/xovis_ibex.properties | grep 'webgui.user' | cut -f2 -d'=' | tr -d [:space:]`
passwd=`cat /opt/xovis/status/xovis_ibex.properties | grep 'webgui.passwd' | cut -f2 -d'=' | tr -d [:space:]`
/usr/bin/htpasswd -cdb /var/www/status/.htpasswd ${user} ${passwd}

# Restart the Apache Web Server
#/sbin/service httpd restart
/usr/sbin/service apache2 restart
