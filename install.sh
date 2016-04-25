#!/bin/bash

if [ ! -f /usr/bin/psql ];  then 
    echo "Postgres is not installed, Installing..."
    yum -y install postgresql92-server postgresql92-devel gcc
    /sbin/service postgresql92 initdb
    /sbin/service postgresql92 restart
    su postgres -c "/usr/bin/psql -U postgres -c \"alter user postgres password 'postgres'\"" >/dev/null
fi

cat > /var/lib/pgsql92/data/pg_hba.conf << EOF
# TYPE   DATABASE    USER    ADDRESS    METHOD    OPTIONS
local    all         all                password
host     all         all     all        password
EOF

if [ -f ~/.pgpass ]; then
    grep "xovis" ~/.pgpass > /dev/null
    if [ $? -ne 0 ]; then
        echo "localhost:*:*:xovis:xovis" >> ~/.pgpass
    fi
else
    echo "localhost:*:*:postgres:postgres" >> ~/.pgpass
    echo "localhost:*:*:xovis:xovis" >> ~/.pgpass
    chmod 600 ~/.pgpass
fi

/sbin/service postgresql92 restart

# Create Xovis config database
/usr/bin/psql -Upostgres -f CreateDatabase.sql

# Upgrade pip
pip install --upgrade pip

# Install python postgres package
pip install psycopg2

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
cp 1_status.conf /etc/httpd/conf.d/

user=`cat /opt/xovis3/xovis_remote_manager.properties | grep 'webgui.user' | cut -f2 -d'=' | tr -d [:space:]`
passwd=`cat /opt/xovis3/xovis_remote_manager.properties | grep 'webgui.passwd' | cut -f2 -d'=' | tr -d [:space:]`
/usr/bin/htpasswd -cdb /var/www/status/.htpasswd ${user} ${passwd}

# Restart the Apache Web Server
/sbin/service httpd restart
