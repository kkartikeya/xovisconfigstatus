import ConfigParser
import urllib2, base64
import xml.etree.ElementTree as ET
import psycopg2
import requests
import socket
import json
import ssl

# Xovis Database Info
DB_HOST='localhost'
DB_NAME='xovis'
DB_USER='xovis'
DB_PASS='networks'

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

def connect():
        conn = psycopg2.connect("dbname = %s host = %s user = %s password = %s" % (DB_NAME, DB_HOST, DB_USER, DB_PASS) )
        cursor = conn.cursor()
        return cursor, conn

def commit( conn ):
    conn.commit();

def rollback():
    conn.rollback();

def parseProperties(propertiesFile):
    config = ConfigParser.RawConfigParser()
    config.read( propertiesFile )

    username = config.get("login", "webgui.user")
    password = config.get("login", "webgui.passwd")
    ipaddress = config.get("login", "webgui.ip")

    return username, password, ipaddress

def getCamConfig(ipaddress, username, password):
    cursor, conn = connect()
    base64string = base64.encodestring('%s:%s' %(username, password)).replace('\n', '')

    getCamListQuery="select macaddress from xovis.xovis_status where connected = true"
    cursor.execute( getCamListQuery )
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    rows = cursor.fetchall()
    for row in rows:
        macaddress=row[0]

        httprequest = urllib2.Request('https://%s/api/v1/devices/%s/access/api/config' % (ipaddress, macaddress))
        httprequest.add_header("Authorization", "Basic %s" % base64string)

        try:
            configXML = urllib2.urlopen(httprequest, timeout=60, context=ctx).read()
            config = ET.fromstring(configXML)

            onpremagentid=cloudcountagentid=cloudsensorstatusagentid=-1

            #Get timezone from the config
            timezone=config.find('sensor').find('timezone').text

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

#            if globalcountmode <> 'LATE':
#                sendSlackMessage( 'Camera: %s for Store: %s is not set to LATE mode.' % ( row[2], row[1] ))

            agents = config.find('datapush')
            if agents!=None:
                for agent in agents.findall('agent'):
                    connector=agent.find('connector')
                    if connector!=None:
                        urlobject=connector.find('url')
                        if urlobject!=None:
                            url=urlobject.text
                            if "datafeed" in url:
                                onpremagentid=agent.attrib.get('id')

                            if "retailops" in url:
                                type=agent.attrib.get('type')
                                id=agent.attrib.get('id')
                                if "countdata" in type:
                                    cloudcountagentid=id

                                if "status" in type:
                                    cloudsensorstatusagentid=id

            cursor.execute( "update xovis.xovis_status set timezone=%s, countmode=%s, coordinatemode=%s, onpremagentid=%s, cloudcountagentid=%s, cloudsensorstatusagentid=%s, config=%s where macaddress=%s", (timezone, globalcountmode, coordinatemode, onpremagentid, cloudcountagentid, cloudsensorstatusagentid, configXML, macaddress))
        except socket.timeout:
            print('Socket Timeout exception for %s' % macaddress)
        except ET.ParseError as err:
            print('Parsing Error for %s' % macaddress)
        except urllib2.URLError as e:
            print("http error %s" % macaddress)
        except ssl.SSLError as e:
            print("SSL error %s" % macaddress)

    commit(conn)
    cursor.close()

def main():
    username, password, ipaddress = parseProperties("/opt/xovis/status/xovis_ibex.properties")
    getCamConfig(ipaddress, username, password)

if __name__ == "__main__":
    main()
