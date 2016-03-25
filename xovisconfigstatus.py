import urllib2, base64
import xml.etree.ElementTree as ET
import ConfigParser
import subprocess

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

def parseSensorsXML(ipaddress, sensorsXML, username, password):
	htmlSnippet = ""
	xmlRoot = ET.fromstring(sensorsXML)
	base64string = base64.encodestring('%s:%s' %(username, password)).replace('\n', '')
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

			if connected == 'true':
				htmlSnippet += str("\n<tr>\n<td><img src=\"resources/images/green_dot.png\" alt=\"Connected\"></td>" )
			else:
				htmlSnippet += str("\n<tr>\n<td><img src=\"resources/images/red_dot.png\" alt=\"Not Connected\"></td>" )

			htmlSnippet += str("\n<td>%s</td>\n<td>%s</td>" % (group, name))
			htmlSnippet += str("\n<td><a href=\"/sensors/%s/\" target=\"_blank\">%s</a></td>" % (serial, serial))
			htmlSnippet += str("\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>" % (ip, devicetype, swversion))

			if alive == 'true' and connected == 'true':
				request1 = urllib2.Request("http://%s/sensors/%s/api/config" % (ipaddress, serial))
				request1.add_header("Authorization", "Basic %s" % base64string)

				settingsXML = urllib2.urlopen(request1, timeout=60).read()

				settings = ET.fromstring(settingsXML)
				htmlSnippet += str("\n<td>%s</td>" % (settings.find('sensor').find('timezone').text))
				htmlSnippet += str("\n<td>%s</td>\n<td>%s</td>\n</tr>" % (settings.find('analytics').find('settings').find('cntmode').text, settings.find('analytics').find('settings').find('coordinatemode').text))
			else:
				htmlSnippet += str("\n<td></td>\n<td></td>\n</tr>")
	return htmlSnippet

def createIndexHTML(htmlSnippet):
	with open("/var/www/status/index.html", "wt") as fout:
		with open("template.html", "rt") as fin:
			for line in fin:
				fout.write(line.replace("####XOVIS####", htmlSnippet))

	subprocess.call(['chmod', '0755', '/var/www/status/index.html'])
		

def main():
	username, password = parseProperties("/opt/xovis3/xovis_remote_manager.properties")
	sensorsXML = fetchSensorsXML("localhost:8080", username, password);
	htmlSnippet = parseSensorsXML( "localhost:8080", sensorsXML, username, password )
	createIndexHTML(htmlSnippet)


if __name__ == "__main__":
	main()

