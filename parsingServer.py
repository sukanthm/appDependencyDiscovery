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
                elif line[0].strip() == "hostName":
                    hostName = line[1].strip()
                elif line[0].strip() == "private ip":
                    hostDetails = hostDetails.append(dict(zip(hostDetails.columns, [FQDN, line[1].strip()])) ,ignore_index=True)
                elif line[0].strip() == "public ip":
                    hostDetails = hostDetails.append(dict(zip(hostDetails.columns, [FQDN, line[1].strip()])) ,ignore_index=True)
        #os.remove(filename)
    elif filename.startswith("tcpDump"):
        with open(filename) as f:
            tcpDump += [x.split() for x in f.read().splitlines()]
        #os.remove(filename)
    elif filename.startswith("sockets"):
        FQDN = filename.replace('sockets_','')[:-16]
        with open(filename) as f:
            for line in f:
                if re.search(r"^\d*_\d*$",line):
                    dateTime = int(line.strip().replace('_',''))
                else:
                    line = [x.replace('\n','') for x in line.split('#')]
                    matches = re.finditer(r"\"(.*)\"", line[3], re.MULTILINE)
                    line[3]=[]
                    for matchNum, match in enumerate(matches):
                        line[3].append(match.group().replace('"',''))
                    sockets = sockets.append(dict(zip(sockets.columns, [FQDN, dateTime, line[1].split(':')[-1], line[0], line[3]])), ignore_index=True)                        
        #os.remove(filename)

tcpDump = pd.DataFrame(tcpDump, columns = ['date','time','del1','src','del2','dst','protocol','del3'])
tcpDump['dateTime'] = tcpDump['date'].str.replace('-','') + tcpDump['time'].str.replace(':','')
del tcpDump['del1']; del tcpDump['del2']; del tcpDump['del3']; del tcpDump['date']; del tcpDump['time'];
tcpDump['port'] = ''
tcpDump['process'] = ''

for index, row in tcpDump.iterrows():
    tcpDump.at[index,'port'] = row['dst'].split('.')[-1].replace(':','')
    tcpDump.at[index,'dst'] = '.'.join(row['dst'].split('.')[:len(row['dst'].split('.'))-1])
    tcpDump.at[index,'dateTime'] = int(row['dateTime'].split('.')[0])

for index, row in tcpDump.iterrows():
    try:
        tcpDump.at[index,'src'] = hostDetails[hostDetails.ip == '.'.join(row['src'].split('.')[:len(row['src'].split('.'))-1])]['FQDN'].item()
    except:
        tcpDump.at[index,'src'] = '.'.join(row['src'].split('.')[:len(row['src'].split('.'))-1])

    dateTime = max(sockets.loc[(sockets['FQDN']==row['dst']) & (sockets['port']==row['port']) & (sockets['dateTime']<=row['dateTime'])]['dateTime'])
    tcpDump.at[index,'process'] = sockets.loc[(sockets['FQDN']==row['dst']) & (sockets['port']==row['port']) & (sockets['dateTime']==dateTime)]['process'].item()

print tcpDump
