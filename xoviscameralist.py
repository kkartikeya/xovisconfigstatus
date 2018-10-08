import urllib2, base64
import ConfigParser
import csv
import datetime
import time
import argparse
import psycopg2
import dateutil.parser as dateparser
import socket
import ssl
import xml.etree.ElementTree as ET
import json

# Xovis Database Info
DB_HOST='localhost'
DB_NAME='xovis'
DB_USER='xovis'
DB_PASS='networks'

def parseProperties(propertiesFile):
    config = ConfigParser.RawConfigParser()
    config.read( propertiesFile )

    username = config.get('login', 'webgui.user')
    password = config.get('login', 'webgui.passwd')
    ipaddress = config.get('login', 'webgui.ip')

    return username, password, ipaddress

username, password, ipaddress = parseProperties("/opt/xovis/status/xovis_ibex.properties")
base64string = base64.encodestring('%s:%s' %(username, password)).replace('\n', '')

def date_to_epoch(dt):
    if dt <> None:
        return time.mktime(time.strptime(dt.strftime('%Y-%m-%d %H:%M:%S.%f'), "%Y-%m-%d %H:%M:%S.%f")) * 1000
    else:
        return 0

def connect():
  conn = psycopg2.connect("dbname = %s host = %s user = %s password = %s" % (DB_NAME, DB_HOST, DB_USER, DB_PASS) )
  cursor = conn.cursor()
  return cursor, conn

def commit( conn ):
    conn.commit();

def rollback():
    conn.rollback();

def getSensorList():
    ''' Get the Sensor List '''
    cursor, conn=connect()
    cursor.execute('select sensorasset_id, sensorgroup, name, ip, serial, devicetype, version, lastconnected from ibex.sensorasset')
    rows = cursor.fetchall()

    return rows

def persistToDb( sensorList, sensorStates ):
    cursor, conn = connect()

    for sensor in sensorList:
        sensor_id, group, name, ip, macaddress, devicetype, swversion, lastconnected = sensor
        connected = getSensorState(macaddress, sensorStates)

        checkCamExist="select macaddress from xovis.xovis_status where macaddress = '%s' " % (macaddress)
        cursor.execute( checkCamExist )
        records = cursor.fetchall()
        curr=date_to_epoch(lastconnected)

        onpremenabled, onprempushstatus, cloudenabled, cloudcountpushstatus, cloudsensorpushstatus, ntpenabled, ntpstatus = getCamStatusByVersion(macaddress,swversion)
        if not records:
            cursor.execute( "insert into xovis.xovis_status(sensor_id, macaddress, sensorgroup, sensorname, lastseen, ipaddress, devicetype, firmware, connected, onpremenabled, \
                           onprempushstatus, cloudenabled, cloudcountpushstatus, cloudsensorpushstatus, ntpenabled, ntpstatus) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, \
                           %s, %s, %s, %s, %s, %s, %s) " , ( sensor_id, macaddress, group, name, curr, ip, devicetype, swversion, connected, onpremenabled, onprempushstatus, \
                            cloudenabled, cloudcountpushstatus, cloudsensorpushstatus, ntpenabled, ntpstatus ) )
        else:
            cursor.execute( "update xovis.xovis_status set sensorgroup = %s, sensorname = %s, lastseen = %s, ipaddress = %s, devicetype = %s, firmware = %s, connected = %s, \
                           onpremenabled = %s, onprempushstatus = %s, cloudenabled = %s, cloudcountpushstatus = %s, cloudsensorpushstatus = %s, ntpenabled = %s, ntpstatus = %s \
                           where sensor_id = %s " , ( group, name, curr, ip, devicetype, swversion, connected, onpremenabled, onprempushstatus, cloudenabled, cloudcountpushstatus, \
                           cloudsensorpushstatus, ntpenabled, ntpstatus, sensor_id ) )

    commit( conn )
    cursor.close();

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
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        httprequest=urllib2.Request('https://%s/api/v1/devices/%s/access/api/info/status' % (ipaddress, macaddress))
        httprequest.add_header("Authorization", "Basic %s" % base64string)

        statusXML = urllib2.urlopen(httprequest, timeout=60, context=ctx).read()
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
    except urllib2.URLError as e:
        print("http error %s" % macaddress)
    except socket.timeout as e:
        print("http error %s" % macaddress)
    except ssl.SSLError as e:
        print("SSL error %s" % macaddress)
    return onpremenabled, onprempushstatus, cloudenabled, cloudcountpushstatus, cloudsensorpushstatus, ntpenabled, ntpstatus

def pullSensorState():
    try:
        httprequest = urllib2.Request('https://%s/api/v1/devices' % (ipaddress))
        httprequest.add_header("Authorization", "Basic %s" % base64string)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        stateJSON = urllib2.urlopen(httprequest, timeout=60, context=ctx).read()

        rows = {}
        parsed_json = json.loads(stateJSON)
        for child in parsed_json:
            state = child['state']
            serial = child['serial']
            rows[serial] =  state
        return rows
    except urllib2.URLError as e:
        print("http error")
    except socket.timeout as e:
        print("http error")
    except ssl.SSLError as e:
        print("SSL error")

def getSensorState(macaddress, sensorStates):
#    OK, UNKNOWN, WARNING, ERROR
    state = sensorStates[macaddress]
    if (state == 'OK' or state == 'WARNING'):
        return True
    else:
        return False

def getCamStatus(macaddress):
    onpremenabled=onprempushstatus=cloudenabled=cloudcountpushstatus=cloudsensorpushstatus=ntpenabled=ntpstatus='false'
    getAgentIdsQuery="select macaddress, onpremagentid, cloudcountagentid, cloudsensorstatusagentid from xovis_status where macaddress='%s' " % (macaddress)
    cursor, conn=connect()
    cursor.execute(getAgentIdsQuery)
    rows=cursor.fetchall()

    if len(rows)>0:
        macaddress=rows[0][0]
        onpremagentid=rows[0][1]
        cloudcountagentid=rows[0][2]
        cloudsensorstatusagentid=rows[0][3]

        try:
            httprequest=urllib2.Request('https://%s/api/v1/devices/%s/access/api/info/status' % (ipaddress, macaddress))
            httprequest.add_header("Authorization", "Basic %s" % base64string)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            statusXML = urllib2.urlopen(httprequest, timeout=60, context=ctx).read()
            try:
                status = ET.fromstring(statusXML)

                datapushstatus = status.find('{http://www.xovis.com/status}data-push-agents')

                if datapushstatus!=None:
                    for agentstatus in datapushstatus.findall('{http://www.xovis.com/status}push-agent'):
                        id=agentstatus.attrib.get('id')

                        if id == onpremagentid:
                            onpremenabled='true'
                            lastsuccessfulText=getElementValue(agentstatus.find('{http://www.xovis.com/status}last-successful'))
                            lastunsuccessfulText=getElementValue(agentstatus.find('{http://www.xovis.com/status}last-unsuccessful'))
                            onprempushstatus=getStatus(lastsuccessfulText, lastunsuccessfulText)

                        if id == cloudcountagentid or id == cloudsensorstatusagentid:
                            cloudenabled='true'
                            if id == cloudcountagentid:
                                lastsuccessfulText=getElementValue(agentstatus.find('{http://www.xovis.com/status}last-successful'))
                                lastunsuccessfulText=getElementValue(agentstatus.find('{http://www.xovis.com/status}last-unsuccessful'))
                                cloudcountpushstatus=getStatus(lastsuccessfulText, lastunsuccessfulText)
                            if id == cloudsensorstatusagentid:
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
        except urllib2.URLError as e:
            print("http error %s" % macaddress)
        except socket.timeout as e:
            print("http error %s" % macaddress)
        except ssl.SSLError as e:
            print("SSL error %s" % macaddress)

    return onpremenabled, onprempushstatus, cloudenabled, cloudcountpushstatus, cloudsensorpushstatus, ntpenabled, ntpstatus

def getCamStatusByVersion(macaddress, firmware):
    if firmware >= '3.5.3':
        onpremenabled, onprempushstatus, cloudenabled, cloudcountpushstatus, cloudsensorpushstatus, ntpenabled, ntpstatus = getCamStatus(macaddress)
    else:
        onpremenabled, onprempushstatus, cloudenabled, cloudcountpushstatus, cloudsensorpushstatus, ntpenabled, ntpstatus = getCamStatusCompatibilityMode(macaddress)

    return onpremenabled, onprempushstatus, cloudenabled, cloudcountpushstatus, cloudsensorpushstatus, ntpenabled, ntpstatus

def persistToCSV( rows, filename ):
    with open(filename, 'wb') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',', dialect='excel')
        csvwriter.writerow(['Serial', 'Sensor Group', 'Sensor Name', 'IP Address', 'Device Type', 'Firmware', 'Connected'])

        for row in rows:
            serial, group, name, ip, devicetype, swversion, connected = row
            csvwriter.writerow([serial, group, name, ip, devicetype, swversion, connected])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csvoutput", help="Use this option for CSV output of the sensor list", action="store_true")
    args = parser.parse_args()

    sensorList = getSensorList()
    sensorState = pullSensorState()

    if args.csvoutput:
        filename = 'xovis_cameras_'+ipaddress + '_' + datetime.datetime.utcnow().isoformat() + '.csv'
        persistToCSV( sensorList, filename )
    else:
        persistToDb( sensorList, sensorState )

if __name__ == "__main__":
    main()
