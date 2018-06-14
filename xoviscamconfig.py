import ConfigParser
import urllib2, base64
import xml.etree.ElementTree as ET
import psycopg2
import requests
import socket
import json

# Xovis Database Info
DB_HOST='localhost'
DB_NAME='xovis'
DB_USER='xovis'
DB_PASS='xovis'

# Slack URL
URL="Enter Slack incoming webhook URL"

def sendSlackMessage( message ):
    if message <> '':
        message = message + "Please fix it ASAP!"
        headers = { 'Content-type': 'application/json' }

        payload = {
            'text': message,
            'username': 'webhookbot',
            'channel': '#slackchannel',
        }
#   requests.post(URL, data=json.dumps(payload), headers=headers)

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

    getCamListQuery="select macaddress, sensorgroup, sensorname from xovis_status where alive = true"
    cursor.execute( getCamListQuery )

    rows = cursor.fetchall()
    for row in rows:
        macaddress=row[0]

        httprequest = urllib2.Request('http://%s/sensors/%s/api/config' % (ipaddress, macaddress))
        httprequest.add_header("Authorization", "Basic %s" % base64string)

        try:
            configXML = urllib2.urlopen(httprequest, timeout=60).read()
            config = ET.fromstring(configXML)

            #Get timezone from the config
            timezone=config.find('sensor').find('timezone').

            #Get Count Mode from the globel config setting, for older version of xovis, the count mode was saved per camera basisself.
            #on the newer version, the count mode is saved as a per count line.
            globalcountmode=config.find('analytics').find('settings').find('cntmode').text
            coordinatemode=config.find('analytics').find('settings').find('coordinatemode').text

            #Get the count mode from the count line and always assuming there will be only one count line.
            try:
                countlinecountmode=config.find('analytics').find('counting').find('cntline').attrib.get('count-mode')
                if countlinecountmode != None:
                    globalcountmode=countlinecountmode
            except AttributeError:
                print("Older Version or Slave Camera")

            if globalcountmode <> 'LATE':
                sendSlackMessage( 'Camera: %s for Store: %s is not set to LATE mode.' % ( row[2], row[1] ))

            agents = config.find('{http://www.xovis.com/config}datapush')
            for agent in agents.findall('{http://www.xovis.com/config}agent'):
                url=agent.find('connector').find('url').text
                if "datafeed" in url:
                    onpremagentid=agent.attrib.get('id').text

                if "retailops" in url:
                    if "countdata" in agent.attrib.get('type').text:
                        cloudcountagentid=agent.attrib.get('id').text

                    if "status" in agent.attrib.get('type').text:
                        cloudsensorstatusagentid=agent.attrib.get('id').text

            config.find('datapush').find('agent').find('connector').find('url').text

            cursor.execute( "update xovis_status set timezone=%s, countmode=%s, coordinatemode=%s, onpremagentid=%s, cloudcountagentid=%s, cloudsensorstatusagentid=%s, config=%s where macaddress=%s", (timezone, globalcountmode, coordinatemode, onpremagentid, cloudcountagentid, cloudsensorstatusagentid, configXML, macaddress))
        except socket.timeout:
            print('Socket Timeout exception for %s' % macaddress)
        except ET.ParseError as err:
            print('Parsing Error')

    commit(conn)
    cursor.close()

def main():
    username, password = parseProperties("/opt/xovis/xovis_remote_manager.properties")
    ipaddress='localhost'
    getCamConfig(ipaddress+':8080', username, password)


if __name__ == "__main__":
    main()
