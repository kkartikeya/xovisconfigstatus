import psycopg2
import subprocess
import datetime
import ConfigParser

# Xovis Database Info
DB_HOST='localhost'
DB_NAME='xovis'
DB_USER='xovis'
DB_PASS='networks'

def parseProperties(propertiesFile):
    config = ConfigParser.RawConfigParser()
    config.read( propertiesFile )

    wanip = config.get('login', 'webgui.wan.ip')

    return wanip

wanip= parseProperties("/opt/xovis/status/xovis_ibex.properties")
def connect():
  conn = psycopg2.connect("dbname = %s host = %s user = %s password = %s" % (DB_NAME, DB_HOST, DB_USER, DB_PASS) )
  cursor = conn.cursor()
  return cursor, conn

def pullSensorHierarchy():
    assetQuery = 'select asset_id, parent_id from ibex.asset'
    cursor, conn = connect()
    cursor.execute(assetQuery)
    result=cursor.fetchall()

    assetInfo = {}
    for row in result:
        asset_id, parent_id = row
        assetInfo[asset_id] = parent_id

    categoryQuery = 'select category_id, parent_id, name from ibex.category'
    cursor.execute(categoryQuery)
    result=cursor.fetchall()

    categoryInfo = {}
    for row in result:
        category_id, parent_id, name = row
        categoryInfo[category_id] = (parent_id, name)

    return assetInfo, categoryInfo

def getCamInfo():
    getCamInfoQuery='select sensor_id, macaddress, sensorgroup, sensorname, lastseen, ipaddress, timezone, devicetype, firmware, ' \
                    'connected, countmode, coordinatemode, onpremenabled, onprempushstatus, cloudenabled, '\
                    'cloudcountpushstatus, cloudsensorpushstatus, ntpenabled, ntpstatus from xovis_status order by sensorgroup asc, sensorname asc, ipaddress asc, lastseen desc'

    cursor, conn = connect()
    cursor.execute( getCamInfoQuery )
    rows=cursor.fetchall()
    return rows

def getParents( sensor_id, assetInfo, categoryInfo):
    self_id = assetInfo[sensor_id]
    parent_id, name = categoryInfo[self_id]

    chain = []
    while parent_id!=None:
        parent_id, name = categoryInfo[parent_id]
        if parent_id <> None:
            chain.append(name)

    return reversed(chain)

epoch = datetime.datetime.utcfromtimestamp(0)

def unix_time_millis(dt):
    return (dt - epoch).total_seconds() * 1000

def current_time_millis():
    current = datetime.datetime.utcnow()
    return int(unix_time_millis( current ))

def getLastSeenText(lastseen):
    currenttime=current_time_millis()
    when=currenttime-lastseen
    return str(when/1000)+' secs ago'

def getSortedRows(assetInfo, categoryInfo):
    rows=getCamInfo()
    tempTableQuery = 'create temp table sensorlist(parents character varying(256), macaddress character varying(18), sensorgroup character varying(256), sensorname character varying(256), lastseen bigint, \
                                     ipaddress character varying(15), timezone character varying(36), devicetype character varying(10), firmware character varying(32), \
                                     connected boolean, countmode character varying(15), coordinatemode character varying(10), onpremenabled boolean, onprempushstatus boolean, \
                                     cloudenabled boolean, cloudcountpushstatus boolean, cloudsensorpushstatus boolean, ntpenabled boolean, \
                                     ntpstatus boolean)'
    cursor, conn = connect()
    cursor.execute( tempTableQuery )

    for row in rows:
        sensor_id, macaddress, sensorgroup, sensorname, lastseen, ipaddress, timezone, devicetype, firmware, connected, countmode, coordinatemode, onpremenabled, onprempushstatus, cloudenabled, cloudcountpushstatus, cloudsensorpushstatus, ntpenabled, ntpstatus = row
        parents = getParents( sensor_id, assetInfo, categoryInfo )
        cursor.execute("insert into sensorList values( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)" , (" > ".join(parents), macaddress, sensorgroup, sensorname, lastseen, ipaddress, timezone, devicetype, firmware, connected, countmode, coordinatemode, onpremenabled, onprempushstatus, cloudenabled, cloudcountpushstatus, cloudsensorpushstatus, ntpenabled, ntpstatus))

    getCamInfoQuery='select parents, macaddress, sensorgroup, sensorname, lastseen, ipaddress, timezone, devicetype, firmware, ' \
                        'connected, countmode, coordinatemode, onpremenabled, onprempushstatus, cloudenabled, '\
                        'cloudcountpushstatus, cloudsensorpushstatus, ntpenabled, ntpstatus from sensorList order by parents asc, sensorgroup asc, sensorname asc, ipaddress asc, lastseen desc'

    cursor.execute(getCamInfoQuery)
    rows=cursor.fetchall()

    dropTempTableQuery = 'drop table sensorList'
    cursor.execute(dropTempTableQuery)
    cursor.close()
    conn.close()
    return rows

def generatehtmlSnippet(assetInfo, categoryInfo):
    htmlSnippet = ""
    rows = getSortedRows(assetInfo, categoryInfo)

    for row in rows:
        parents, macaddress, sensorgroup, sensorname, lastseen, ipaddress, timezone, devicetype, firmware, connected, countmode, coordinatemode, onpremenabled, onprempushstatus, cloudenabled, cloudcountpushstatus, cloudsensorpushstatus, ntpenabled, ntpstatus = row

        if connected:
            htmlSnippet += str('\n<tr>\n<td><img src="resources/images/green_dot.png" alt="Connected" /></td>' )
        else:
            htmlSnippet += str('\n<tr>\n<td><img src="resources/images/red_dot.png" alt="Not Connected" /></td>' )

        htmlSnippet += str('\n<td>%s</td>' % (parents))

        htmlSnippet += str('\n<td>%s</td>\n<td>%s</td>' % (sensorgroup, sensorname))

        htmlSnippet += str('\n<td>%s</td>' % (getLastSeenText(lastseen)))
        htmlSnippet += str('\n<td><a href="https://%s/api/v1/devices/%s/access" target="_blank">%s</a></td>' % (wanip, macaddress, macaddress))
        htmlSnippet += str('\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>' % (ipaddress, devicetype, firmware))

        if connected:
            htmlSnippet += str('\n<td>%s</td>' % (timezone))

            if ntpenabled:
                htmlSnippet += str('\n<td><input type="checkbox" disabled="disabled" checked /></td>')
                if ntpstatus:
                    htmlSnippet += str('\n<td><img src="resources/images/green_dot.png" alt="Success" /></td>' )
                else:
                    htmlSnippet += str('\n<td><img src="resources/images/red_dot.png" alt="Fail" /></td>' )
            else:
                htmlSnippet += str('\n<td><input type="checkbox" disabled="disabled" unchecked /></td>\n<td></td>')

            htmlSnippet += str("\n<td>%s</td>\n<td>%s</td>" % (countmode, coordinatemode))

            if onpremenabled:
                htmlSnippet += str('\n<td><input type="checkbox" disabled="disabled" checked /></td>')
                if onprempushstatus:
                    htmlSnippet += str('\n<td><img src="resources/images/green_dot.png" alt="Success" /></td>' )
                else:
                    htmlSnippet += str('\n<td><img src="resources/images/red_dot.png" alt="Fail" /></td>' )
            else:
                htmlSnippet += str('\n<td><input type="checkbox" disabled="disabled" unchecked /></td>\n<td></td>')

            if cloudenabled:
                htmlSnippet += str('\n<td><input type="checkbox" disabled="disabled" checked /></td>')

                if cloudcountpushstatus:
                    htmlSnippet += str('\n<td><img src="resources/images/green_dot.png" alt="Success" /></td>' )
                else:
                    htmlSnippet += str('\n<td><img src="resources/images/red_dot.png" alt="Fail" /></td>' )

                if cloudsensorpushstatus:
                    htmlSnippet += str('\n<td><img src="resources/images/green_dot.png" alt="Success" /></td>' )
                else:
                    htmlSnippet += str('\n<td><img src="resources/images/red_dot.png" alt="Fail" /></td>' )
            else:
                htmlSnippet += str('\n<td><input type="checkbox" disabled="disabled" unchecked /></td>\n<td></td>\n<td></td>\n</tr>\n')
        else:
            htmlSnippet += str('\n<td></td>\n<td></td>\n<td></td>\n<td></td>\n<td></td>\n<td></td>\n<td></td>\n<td></td>\n<td></td>\n<td></td>\n</tr>\n')
    return htmlSnippet

def createIndexHTML(htmlSnippet):
    with open("/var/www/status/index.html", "wt") as fout:
        with open("template.html", "rt") as fin:
            for line in fin:
                fout.write(line.replace("####XOVIS####", htmlSnippet))

    subprocess.call(['chmod', '0755', '/var/www/status/index.html'])


def main():
    assetInfo, categoryInfo = pullSensorHierarchy()
    htmlSnippet = generatehtmlSnippet(assetInfo, categoryInfo)
    createIndexHTML(htmlSnippet)

if __name__ == "__main__":
    main()
