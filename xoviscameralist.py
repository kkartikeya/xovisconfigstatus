import urllib2, base64
import xml.etree.ElementTree as ET
import ConfigParser
import csv
import datetime

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

def parseProperties(propertiesFile):
	config = ConfigParser.SafeConfigParser()
	config.readfp( FakeSecHead(open(propertiesFile )))

	username = config.get("asection", "webgui.user")
	password = config.get("asection", "webgui.passwd")

	return username, password


def fetchSensorsXML(ipaddress, username, password):
	''' Get the Sensor List '''
	request = urllib2.Request("http://%s/sensors" % (ipaddress))
	base64string = base64.encodestring('%s:%s' %(username, password)).replace('\n', '')
	request.add_header("Authorization", "Basic %s" % base64string)
	sensorsXML = urllib2.urlopen(request, timeout=60).read()

	return sensorsXML

def parseSensorsXML(sensorsXML, filename):

	with open(filename, 'wb') as csvfile:
		csvwriter = csv.writer(csvfile, delimiter=',', dialect='excel')
		csvwriter.writerow(['Serial', 'Sensor Group', 'Sensor Name', 'IP Address', 'Device Type', 'Firmware', 'Registered', 'Alive', 'Connected'])

		xmlRoot = ET.fromstring(sensorsXML)
		for child in xmlRoot:
			if child.tag == 'sensor':
				serial = child.find('serial').text
				ip = child.find('ip').text
				group = child.find('group').text
				name = child.find('name').text
				devicetype = child.find('device-type').text
				swversion = child.find('sw-version').text
				registered = child.find('registered').text
				alive = child.find('alive').text
				connected = child.find('connected').text
				csvwriter.writerow(['%s, %s, %s, %s, %s, %s, %s, %s, %s' % (serial, group, name, ip, devicetype, swversion, registered, alive, connected)])



def main():
	username, password = parseProperties("/opt/xovis3/xovis_remote_manager.properties")
	ipaddress = 'localhost'
	sensorsXML = fetchSensorsXML(ipaddress+':8080', username, password);
	filename = 'xovis_cameras_'+ipaddress + '_' + datetime.datetime.utcnow().isoformat() + '.csv'
	parseSensorsXML( sensorsXML, filename )

if __name__ == "__main__":
	main()
