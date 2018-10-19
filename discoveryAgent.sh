if [ -z "$1" ]; then
    counter=600
    echo running app dependency discovery agent for $counter seconds \(default\)
else
    counter=$1
    echo running app dependency discovery agent for $counter seconds
fi

fqdn=$(hostname).$(hostname -d)  # hostname -f fails if no dns name is set
hostName=$(hostname)
ipPrivate1=($(hostname -i))
ipPrivate2=($(hostname -I))
ipPublic=($(dig +short myip.opendns.com @resolver1.opendns.com))
ipString1=""
ipString2=""

echo FQDN = $fqdn; echo FQDN = $fqdn &> hostDetails_${fqdn}
echo hostName = $hostName >> hostDetails_${fqdn}
for i in "${ipPrivate1[@]}"
do
    echo private ip = "$i" >> hostDetails_${fqdn}
    ipString1=" $ipString1 dst host $i or "
    ipString2=" $ipString2 s/$i/${fqdn}/g; "
done
for i in "${ipPrivate2[@]}"
do
    echo private ip = "$i" >> hostDetails_${fqdn}
    ipString1=" $ipString1 dst host $i or "
    ipString2=" $ipString2 s/$i/${fqdn}/g; "
done
for i in "${ipPublic[@]}"
do
    echo public ip = "$i" >> hostDetails_${fqdn}
    ipString1=" $ipString1 dst host $i or "
    ipString2=" $ipString2 s/$i/${fqdn}/g; "
done
ipString1=" $ipString1 dst host 127.0.0.1 "
awk '!a[$0]++' hostDetails_${fqdn} &> hostDetails.tmp #deL duplicates
mv hostDetails.tmp hostDetails_${fqdn}


dt=$(date '+%Y%m%d_%H%M%S');
echo "$dt" &> sockets_${fqdn}
sudo ss -plntu >> sockets_${fqdn}
var1=$(ss -lntu | awk '{ print $5 }' | grep -oP "[\d]*$" | awk '!a[$0]++' | sort -nk1 | tr '\n' ' ' ) #take 5th column; regex for ports; remove duplicates; sort ascendin;, concat rows
echo started sokcet monitoring
echo current socket list \= $var1

#cmd="nohup sudo tcpdump \"(tcp[tcpflags] == tcp-syn or udp) and ($ipString1)\" -ttttnnqi any &> tcpDump_${fqdn} &"
cmd="nohup sudo tcpdump \"(tcp or udp) and ($ipString1)\" -ttttnnqi any &> tcpDump_${fqdn} &"
echo "executing: $cmd"
eval "$cmd"
pID=$!
echo pID is $pID
printf '\n'

sp="/-\|"
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
                sudo ss -plntu >> sockets_${fqdn}
                awk '!a[$0]++' sockets_${fqdn} &> sockets.tmp #deL duplicates
                mv sockets.tmp sockets_${fqdn}
            fi
            var1=$var2
    fi
    printf "\b${sp:i++%${#sp}:1}"
    sleep 1s
done

printf '\n'
echo interrupting process $pID
sudo kill -s SIGINT $(pgrep -P ${pID})

cmd="sed '1,2d; s/127.0.0.1/${fqdn}/g; ${ipString2}' tcpDump_${fqdn} &> tcpDump.tmp" #del top 2 lines; replace ipPrivate,ipPublic,localhost with FQDN
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

echo script complete \:\)
exit 0
