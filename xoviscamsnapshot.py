import ConfigParser
import urllib2, base64
import xml.etree.ElementTree as ET
import psycopg2
import socket
import argparse

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
    base64string=base64.encodestring('%s:%s' %(username, password)).replace('\n', '')

    request = urllib2.Request("http://%s/sensors" % (ipaddress))
    request.add_header("Authorization", "Basic %s" % base64string)
    sensorsXML = urllib2.urlopen(request, timeout=60).read()

    return sensorsXML

def parseSensorsXML(sensorsXML):
    rows = []
    xmlRoot = ET.fromstring(sensorsXML)
    for child in xmlRoot:
        if child.tag == 'sensor':
            serial = child.find('serial').text
            ip = child.find('ip').text
            group = child.find('group').text
            name = child.find('name').text
            rows.append([serial, group, name, ip])
    return rows

def getCamSnapshot(rows, ipaddress, username, password, passwd):
    base64string = base64.encodestring('%s:%s' %(username, password)).replace('\n', '')

    for row in rows:
        serial=row[0]
        group=row[1]
        name=row[2]
        ip=row[3]
        filename="nike/%s_%s_%s_%s.jpg" % (group, name, ip, serial)

        try:
            url='http://%s/sensors/%s/api/scene/live?passwd=%s' % (ipaddress, serial, passwd)
            httprequest = urllib2.Request(url)
            httprequest.add_header("Authorization", "Basic %s" % base64string)

            image=urllib2.urlopen(httprequest, timeout=120).read()
            if 'Not authorized' in image:
                url='http://%s/sensors/%s/api/scene/live?passwd=%s' % (ipaddress, serial, 'pass')
                httprequest = urllib2.Request(url)
                httprequest.add_header("Authorization", "Basic %s" % base64string)
                image=urllib2.urlopen(httprequest, timeout=120).read()

            with open(filename, 'wb') as out:
                out.write(image)
        except socket.timeout:
            print(url)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--passwd", help="camera password", type=str)
    args = parser.parse_args()

    if args.passwd:
        passwd=args.passwd
    else:
        passwd='pass'

    username, password = parseProperties("/opt/xovis/xovis_remote_manager.properties")
    ipaddress='localhost:8080'

    sensorXML=fetchSensorsXML(ipaddress, username, password)
    rows=parseSensorsXML(sensorXML)
    print("Total Number of cameras: %s" % len(rows))
    getCamSnapshot(rows, ipaddress, username, password, passwd)


if __name__ == "__main__":
    main()
