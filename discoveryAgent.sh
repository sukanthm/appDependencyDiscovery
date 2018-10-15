if [ -z "$1" ]; then
    counter=600
    echo running app dependency discovery agent for $counter seconds \(default\)
else
    counter=$1
    echo running app dependency discovery agent for $counter seconds
fi

fqdn=$(hostname -f)
hostName=$(hostname)
ipPrivate=($(hostname -i))
ipPublic=($(dig +short myip.opendns.com @resolver1.opendns.com))

echo FQDN = $fqdn; echo FQDN = $fqdn &> hostDetails_${fqdn}
#echo hostName = $hostName; 
echo hostName = $hostName >> hostDetails_${fqdn}
#echo private ip = ${ipPrivate[0]}; 
echo private ip = ${ipPrivate[0]} >> hostDetails_${fqdn}
#echo public ip = ${ipPublic[0]}; 
echo public ip = ${ipPublic[0]} >> hostDetails_${fqdn}
#printf "\n"

dt=$(date '+%Y%m%d_%H%M%S');
echo "$dt" &> sockets_${fqdn}
ss -plntu >> sockets_${fqdn}
var1=$(ss -lntu | awk '{ print $5 }' | grep -oP "[\d]*$" | awk '!a[$0]++' | sort -nk1 | tr '\n' ' ' ) #take 5th column; regex for ports; remove duplicates; sort ascendin;, concat rows
echo started sokcet monitoring
echo current socket list \= $var1

cmd="tcpdump \"(tcp[tcpflags] == tcp-syn or udp) and (dst host 127.0.0.1 or dst host ${ipPrivate[0]} or dst host ${ipPublic[0]})\" -ttttnnqi any &> tcpDump_${fqdn}"
echo executing: $cmd
eval "nohup $cmd &"
pID=$!
echo pID is $pID

i=0
while [ $i -lt $counter ]
do
    var2=$(ss -lntu | awk '{ print $5 }' | grep -oP "[\d]*$" | awk '!a[$0]++' | sort -nk1 | tr '\n' ' ' )
    i=$[$i+1]
    
    if [ "$var1" != "$var2" ];then
            dt=$(date '+%Y%m%d_%H%M%S')
            echo socket list changed \= $var2
            if [ ${#var2} -ge ${#var1} ];then
                echo "$dt" >> sockets_${fqdn}
                ss -plntu >> sockets_${fqdn}
                awk '!a[$0]++' sockets_${fqdn} &> sockets.tmp #deL duplicates
                mv sockets.tmp sockets_${fqdn}
            fi
            var1=$var2
    fi
    sleep 1s
done

echo interrupting pID $pID process
kill -s SIGINT $pID

cmd="sed '1,2d; s/${ipPrivate[0]}/${fqdn}/g; s/${ipPublic[0]}/${fqdn}/g; s/127.0.0.1/${fqdn}/g' tcpDump_${fqdn} &> tcpDump.tmp" #del top 2 lines; replace ipPrivate,ipPublic,localhost with FQDN
eval $cmd
sed -n -e :a -e '1,4!{P;N;D;};N;ba' tcpDump.tmp &> tcpDump_${fqdn} #del bottom 4 lines
rm tcpDump.tmp

awk '{$2=$3=$4=null; print $0}' sockets_${fqdn} | sed 's/ /#/g; s/####/#/g; s/###//g; /Netid/d; /^$/d' &> sockets.tmp #del columns 2,3,4; replace delimiter; remove header row; del empty lines
mv sockets.tmp sockets_${fqdn}

dt=$(date '+%Y%m%d_%H%M%S')
mv hostDetails_${fqdn} hostDetails_${fqdn}_${dt}
mv sockets_${fqdn} sockets_${fqdn}_${dt}
mv tcpDump_${fqdn} tcpDump_${fqdn}_${dt}
tar czf ${fqdn}_${dt}.tar.gz hostDetails_${fqdn}_${dt} sockets_${fqdn}_${dt} tcpDump_${fqdn}_${dt} --remove-files
echo ${fqdn}_${dt}.tar.gz created
#curl -kX POST https://ip:443/upload -H "authKey: blah" -d @${fqdn}.tar.gz

echo script complete \:\)
