import urllib2, base64
import xml.etree.ElementTree as ET
import ConfigParser
import csv
import datetime
import argparse
import psycopg2
import dateutil.parser as dateparser
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

def parseProperties(propertiesFile):
    config = ConfigParser.SafeConfigParser()
    config.readfp( FakeSecHead(open(propertiesFile )))

    username = config.get("asection", "webgui.user")
    password = config.get("asection", "webgui.passwd")

    return username, password

username, password = parseProperties("/opt/xovis/xovis_remote_manager.properties")
ipaddress = 'localhost'
base64string = base64.encodestring('%s:%s' %(username, password)).replace('\n', '')
epoch = datetime.datetime.utcfromtimestamp(0)

def unix_time_millis(dt):
    return (dt - epoch).total_seconds() * 1000

def current_time_millis():
    current = datetime.datetime.utcnow()
    return int(unix_time_millis( current ))

def connect():
  conn = psycopg2.connect("dbname = %s host = %s user = %s password = %s" % (DB_NAME, DB_HOST, DB_USER, DB_PASS) )
  cursor = conn.cursor()
  return cursor, conn

def commit( conn ):
    conn.commit();

def rollback():
    conn.rollback();

def fetchSensorsXML(ipaddress, username, password):
    ''' Get the Sensor List '''
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
            devicetype = child.find('device-type').text
            swversion = child.find('sw-version').text
            registered = child.find('registered').text
            alive = child.find('alive').text
            connected = child.find('connected').text
            rows.append([serial, group, name, ip, devicetype, swversion, registered, alive, connected])
    return rows

def getElementValue( object ):
    if object is not None:
        return object.text
    else:
        return None

def getStatus( lastsuccessfulText, lastunsuccessfulText):
    lastsuccessful=None
    lastunsuccessful=None
    status='false'

    if lastsuccessfulText is not None:
        lastsuccessful=dateparser.parse(lastsuccessfulText)

    if lastunsuccessfulText is not None:
        lastunsuccessful=dateparser.parse(lastunsuccessfulText)

    if lastsuccessful is not None and lastunsuccessful is not None:
        if lastsuccessful>lastunsuccessful:
            status='true'
        else:
            status='false'
    elif lastsuccessful is None and lastunsuccessful is not None:
        status='false'
    elif lastsuccessful is not None and lastunsuccessful is None:
        status='true'

    return status

def getCamStatusCompatibilityMode(macaddress):
    onpremenabled=onprempushstatus=cloudenabled=cloudcountpushstatus=cloudsensorpushstatus=ntpenabled=ntpstatus='false'

    try:
        httprequest=urllib2.Request('http://%s/sensors/%s/api/info/status' % (ipaddress, macaddress))
        httprequest.add_header("Authorization", "Basic %s" % base64string)

        statusXML = urllib2.urlopen(httprequest, timeout=60).read()
        try:
            status = ET.fromstring(statusXML)

            datapushstatus = status.find('{http://www.xovis.com/status}data-push-status')

            if datapushstatus!=None:
                for agentstatus in datapushstatus.findall('{http://www.xovis.com/status}agent-status'):
                    agent=agentstatus.find('{http://www.xovis.com/status}agent').text

                    if "datafeed" in agent:
                        onpremenabled='true'
                        lastsuccessfulText=getElementValue(agentstatus.find('{http://www.xovis.com/status}last-successful'))
                        lastunsuccessfulText=getElementValue(agentstatus.find('{http://www.xovis.com/status}last-unsuccessful'))
                        onprempushstatus=getStatus(lastsuccessfulText, lastunsuccessfulText)

                    if "retailops" in agent:
                        cloudenabled='true'
                        if "countdata" in agent:
                            lastsuccessfulText=getElementValue(agentstatus.find('{http://www.xovis.com/status}last-successful'))
                            lastunsuccessfulText=getElementValue(agentstatus.find('{http://www.xovis.com/status}last-unsuccessful'))
                            cloudcountpushstatus=getStatus(lastsuccessfulText, lastunsuccessfulText)
                        if "status" in agent:
                            lastsuccessfulText=getElementValue(agentstatus.find('{http://www.xovis.com/status}last-successful'))
                            lastunsuccessfulText=getElementValue(agentstatus.find('{http://www.xovis.com/status}last-unsuccessful'))
                            cloudsensorpushstatus=getStatus(lastsuccessfulText, lastunsuccessfulText)

            for ntpstatus in status.findall('{http://www.xovis.com/status}ntp-status'):
                ntpenabled=getElementValue(ntpstatus.find('{http://www.xovis.com/status}active'))
                lastsuccessfulText=getElementValue(ntpstatus.find('{http://www.xovis.com/status}last-successful'))
                lastunsuccessfulText=getElementValue(ntpstatus.find('{http://www.xovis.com/status}last-unsuccessful'))
                ntpstatus=getStatus(lastsuccessfulText, lastunsuccessfulText)
        except ET.ParseError:
            print("parsing exception %s " % macaddress)
    except urllib2.URLError, e:
        print("http error %s" % macaddress)
    except socket.timeout, e:
        print("http error %s" % macaddress)

    return onpremenabled, onprempushstatus, cloudenabled, cloudcountpushstatus, cloudsensorpushstatus, ntpenabled, ntpstatus

def getCamStatus(macaddress):
    onpremenabled=onprempushstatus=cloudenabled=cloudcountpushstatus=cloudsensorpushstatus=ntpenabled=ntpstatus='false'
    
    return onpremenabled, onprempushstatus, cloudenabled, cloudcountpushstatus, cloudsensorpushstatus, ntpenabled, ntpstatus

def getCamStatusByVersion(macaddress, firmware):
    if firmware >= '3.5.2':
        onpremenabled, onprempushstatus, cloudenabled, cloudcountpushstatus, cloudsensorpushstatus, ntpenabled, ntpstatus = getCamStatusCompatibilityMode(macaddress)
    else
        onpremenabled, onprempushstatus, cloudenabled, cloudcountpushstatus, cloudsensorpushstatus, ntpenabled, ntpstatus = getCamStatus(macaddress)

    return onpremenabled, onprempushstatus, cloudenabled, cloudcountpushstatus, cloudsensorpushstatus, ntpenabled, ntpstatus

def persistToDb( rows ):
    cursor, conn = connect()
    curr=current_time_millis()

    for row in rows:
        serial, group, name, ip, devicetype, swversion, registered, alive, connected = row

        checkCamExist="select macaddress from xovis_status where macaddress = '%s' " % ( serial )
        cursor.execute( checkCamExist )
        records = cursor.fetchall()

        if alive == 'true':
            onpremenabled, onprempushstatus, cloudenabled, cloudcountpushstatus, cloudsensorpushstatus, ntpenabled, ntpstatus = getCamStatusByVersion(serial,swversion)
            if not records:
                cursor.execute( "insert into xovis_status(macaddress, sensorgroup, sensorname, lastseen, ipaddress, devicetype, firmware, registered, alive, connected, onpremenabled, onprempushstatus, cloudenabled, cloudcountpushstatus, cloudsensorpushstatus, ntpenabled, ntpstatus) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) " , ( serial, group, name, curr, ip, devicetype, swversion, registered, alive, connected, onpremenabled, onprempushstatus, cloudenabled, cloudcountpushstatus, cloudsensorpushstatus, ntpenabled, ntpstatus ) )
            else:
                cursor.execute( "update xovis_status set sensorgroup = %s, sensorname = %s, lastseen = %s, ipaddress = %s, devicetype = %s, firmware = %s, registered = %s, alive = %s, connected = %s, onpremenabled = %s, onprempushstatus = %s, cloudenabled = %s, cloudcountpushstatus = %s, cloudsensorpushstatus = %s, ntpenabled = %s, ntpstatus = %s where macaddress = %s " , ( group, name, curr, ip, devicetype, swversion, registered, alive, connected, onpremenabled, onprempushstatus, cloudenabled, cloudcountpushstatus, cloudsensorpushstatus, ntpenabled, ntpstatus, serial ) )
        else:
            if not records:
                cursor.execute( "insert into xovis_status(macaddress, sensorgroup, sensorname, lastseen, ipaddress, devicetype, firmware, registered, alive, connected) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) " , ( serial, group, name, 0, ip, devicetype, swversion, registered, alive, connected ) )
            else:
                cursor.execute( "update xovis_status set sensorgroup = %s, sensorname = %s, ipaddress = %s, devicetype = %s, firmware = %s, registered = %s, alive = %s, connected = %s where macaddress = %s " , ( group, name, ip, devicetype, swversion, registered, alive, connected, serial ) )

    commit( conn )
    cursor.close();

def persistToCSV( rows, filename ):
    with open(filename, 'wb') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',', dialect='excel')
        csvwriter.writerow(['Serial', 'Sensor Group', 'Sensor Name', 'IP Address', 'Device Type', 'Firmware', 'Registered', 'Alive', 'Connected'])

        for row in rows:
            serial, group, name, ip, devicetype, swversion, registered, alive, connected = row
            csvwriter.writerow([serial, group, name, ip, devicetype, swversion, registered, alive, connected])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csvoutput", help="Use this option for CSV output of the sensor list", action="store_true")
    args = parser.parse_args()

    sensorsXML = fetchSensorsXML(ipaddress+':8080', username, password)

    rows = parseSensorsXML( sensorsXML )
    if args.csvoutput:
        filename = 'xovis_cameras_'+ipaddress + '_' + datetime.datetime.utcnow().isoformat() + '.csv'
        persistToCSV( rows, filename )
    else:
        persistToDb( rows )

if __name__ == "__main__":
    main()
