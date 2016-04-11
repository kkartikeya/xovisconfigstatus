import ConfigParser
import urllib2, base64
import xml.etree.ElementTree as ET
import psycopg2
import socket

# Xovis Database Info
DB_HOST='localhost'
DB_NAME='xovis'
DB_USER='xovis'
DB_PASS='xovis'

class FakeSecHead(object):
    def __init__(self, fp):
        self.fp = fp
        self.sechead = '[asection]\n'

    def readline(self):
        if self.sechead:
            try: 
                return self.sechead
            finally: 
                self.sechead = None
        else: 
            return self.fp.readline()

def connect():
  conn = psycopg2.connect("dbname = %s host = %s user = %s password = %s" % (DB_NAME, DB_HOST, DB_USER, DB_PASS) )
  cursor = conn.cursor()
  return cursor, conn

def commit( conn ):
	conn.commit();

def rollback():
	conn.rollback();

def parseProperties(propertiesFile):
	config = ConfigParser.SafeConfigParser()
	config.readfp( FakeSecHead(open(propertiesFile )))

	username = config.get("asection", "webgui.user")
	password = config.get("asection", "webgui.passwd")

	return username, password

def getCamConfig(ipaddress, username, password):
	cursor, conn = connect()
	base64string = base64.encodestring('%s:%s' %(username, password)).replace('\n', '')

	getCamListQuery="select macaddress from xovis_status where alive = true"
	cursor.execute( getCamListQuery )

	rows = cursor.fetchall()
	for row in rows:
		macaddress=row[0]

		httprequest = urllib2.Request('http://%s/sensors/%s/api/config' % (ipaddress, macaddress))
		httprequest.add_header("Authorization", "Basic %s" % base64string)

		try:
			configXML = urllib2.urlopen(httprequest, timeout=60).read()
			config = ET.fromstring(configXML)
			timezone=config.find('sensor').find('timezone').text
			countmode=config.find('analytics').find('settings').find('cntmode').text
			coordinatemode=config.find('analytics').find('settings').find('coordinatemode').text

			cursor.execute( "update xovis_status set timezone=%s, countmode=%s, coordinatemode=%s, config=%s where macaddress=%s", (timezone, countmode, coordinatemode, configXML, macaddress))
		except socket.timeout:
			print('Socket Timeout exception for %s' % macaddress)
	commit(conn)
	cursor.close()

def main():
	username, password = parseProperties("/opt/xovis3/xovis_remote_manager.properties")
	ipaddress='localhost'
	getCamConfig(ipaddress+':8080', username, password)


if __name__ == "__main__":
	main()