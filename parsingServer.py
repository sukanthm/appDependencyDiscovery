import tarfile
import os
import pandas as pd
import re

for filename in os.listdir(os.getcwd()):
    if filename.endswith(".tar.gz"):
        tar = tarfile.open(filename)
        tar.extractall()
        tar.close()
        #os.remove(filenme)

graph1 = []
graph2 =[]
hostDetails = pd.DataFrame(columns = ['FQDN','ip'])
tcpDump = []
sockets = pd.DataFrame(columns = ['FQDN','dateTime','port','protocol','process'])
for filename in os.listdir(os.getcwd()):
    if filename.startswith("hostDetails"):
        with open(filename) as f:
            for line in f:
                line = line.split('=')
                if line[0].strip() == "FQDN":
                    FQDN = line[1].strip()
                    FQDNgraph =  ''.join([x for x in FQDN if x.isalpha() or x.isdigit()])
                elif line[0].strip() == "hostName":
                    hostName = line[1].strip()
                    graph1.append( "MERGE (n:server {name: '"+FQDN+"'}) SET n.hostName='"+hostName+"';" )
                elif line[0].strip() == "private ip":
                    if line[1].strip() != '127.0.0.1':
                        hostDetails = hostDetails.append(dict(zip(hostDetails.columns, [FQDN, line[1].strip()])) ,ignore_index=True)
                        graph1.append( "MERGE (n:server {name: '"+FQDN+"'}) SET n.ipPrivate='"+line[1].strip()+"';" )
                elif line[0].strip() == "public ip":
                    if line[1].strip() != '127.0.0.1':
                        hostDetails = hostDetails.append(dict(zip(hostDetails.columns, [FQDN, line[1].strip()])) ,ignore_index=True)
                        graph1.append( "MERGE (n:server {name: '"+FQDN+"'}) SET n.ipPublic='"+line[1].strip()+"';" )
        os.remove(filename)
    elif filename.startswith("tcpDump"):
        with open(filename) as f:
            tcpDump += [x.split() for x in f.read().splitlines()]
        os.remove(filename)
    elif filename.startswith("sockets"):
        FQDN = filename.replace('sockets_','')[:-16]
        with open(filename) as f:
            for line in f:
                if re.search(r"^\d*_\d*$",line):
                    dateTime = int(line.strip().replace('_',''))
                else:
                    line = [x.replace('\n','') for x in line.split('#')]
                    matches = re.finditer(r"\"([^\"]*)\"", line[3], re.MULTILINE)
                    line[3]=[]
                    for matchNum, match in enumerate(matches):
                        line[3].append(match.group().replace('"',''))
                    line[3]=', '.join(set(line[3]))
                    sockets = sockets.append(dict(zip(sockets.columns, [FQDN, dateTime, line[1].split(':')[-1], line[0], line[3]])), ignore_index=True)
                    graph1.append( "MERGE (n:app {name: '"+line[3]+"', FQDN: '"+FQDN+"'}) SET n.dateTime='"+ str(dateTime) +"', n.port='"+line[1].split(':')[-1]+"', n.protocol='"+line[0]+"';" )
                    graph2.append("MATCH (b:app) WITH b MATCH (a:server) WHERE a.name = '"+FQDN+"' AND b.FQDN = '"+FQDN+"' AND b.name = '"+line[3] + "' CREATE (a)-[r: HOSTS]->(b); ")
        os.remove(filename)

graph1=list(set(graph1))
graph1.append('CREATE INDEX ON :server(name);')
graph1.append('CREATE INDEX ON :app(name);')
graph1.append('CREATE INDEX ON :app(FQDN);')
graph2=list(set(graph2))

try:
    tcpDump = pd.DataFrame(tcpDump, columns = ['date','time','del1','src','del2','dst','protocol','del3'])
except:
    tcpDump = pd.DataFrame(tcpDump, columns = ['date','time','del1','src','del2','dst','protocol','del3','del4'])
    del tcpDump['del4'];

tcpDump['dateTime'] = tcpDump['date'].str.replace('-','') + tcpDump['time'].str.replace(':','')
del tcpDump['del1']; del tcpDump['del2']; del tcpDump['del3']; del tcpDump['date']; del tcpDump['time'];
tcpDump['port'] = ''
tcpDump['process'] = ''

for index, row in tcpDump.iterrows():
    tcpDump.at[index,'port'] = row['dst'].split('.')[-1].replace(':','')
    tcpDump.at[index,'dst'] = '.'.join(row['dst'].split('.')[:len(row['dst'].split('.'))-1])
    tcpDump.at[index,'dateTime'] = int(row['dateTime'].split('.')[0])
    tcpDump.at[index,'protocol'] = row['protocol'].replace(',','').lower()

for index, row in tcpDump.iterrows():
    try:
        tcpDump.at[index,'src'] = hostDetails[hostDetails.ip == '.'.join(row['src'].split('.')[:len(row['src'].split('.'))-1])]['FQDN'].item()
    except:
        tcpDump.at[index,'src'] = '.'.join(row['src'].split('.')[:len(row['src'].split('.'))-1])

    try:
        dateTime = max(sockets.loc[(sockets['FQDN']==row['dst']) & (sockets['port']==row['port']) & (sockets['protocol']==row['protocol'])  & (sockets['dateTime']<=row['dateTime'])]['dateTime'])
        y=[]
        for x in sockets.loc[(sockets['FQDN']==row['dst']) & (sockets['port']==row['port']) & (sockets['protocol']==row['protocol']) & (sockets['dateTime']==dateTime)]['process'].items():
            y.append(x[1])   
        tcpDump.at[index,'process'] = ', '.join(list(set(y)))
    except:
        pass

output = pd.DataFrame({'hits' : tcpDump.groupby( ['src','dst','port','process'] ).size()}).reset_index()
output = output.drop(output[output.process == ''].index)
output.reset_index(drop=True, inplace=True)
output.to_csv('output.csv', sep='#', index=False)
output.to_html('output.html')

graph3 = []
for index, row in output.iterrows():
    if row['src'] not in list(hostDetails['FQDN']):
        graph3.append( "MERGE (n:client {name: '"+row['src']+"'}) ;" )
graph3.append("CREATE INDEX ON :client(name);")
for index, row in output.iterrows():
    if row['src'] not in list(hostDetails['FQDN']):
        graph3.append("MATCH (b:app) WITH b MATCH (a:client) WHERE a.name = '"+row['src']+"' AND b.FQDN = '"+row['dst']+"' AND b.name = '"+row['process'] + "' CREATE (a)-[r: HITS {Count:"+str(row['hits'])+"}]->(b); ")
    else:
        graph3.append("MATCH (b:app) WITH b MATCH (a:server) WHERE a.name = '"+row['src']+"' AND b.FQDN = '"+row['dst']+"' AND b.name = '"+row['process'] + "' CREATE (a)-[r: HITS {Count:"+str(row['hits'])+"}]->(b); ")

text_file = open("output.txt", "w")
text_file.write('\n'.join(graph1) + '\n'.join(graph2) + '\n'.join(graph3))
text_file.close()
