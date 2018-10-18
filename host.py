from __future__ import print_function
import sys
import libvirt
from xml.dom import minidom
import xml.etree.ElementTree as ET
import re
import subprocess

mapOfMacToDomainName={}
mapOfIpToDomainName={}

def printxml(root):
	if root != None:
		for child in root: 
			printxml(child)
			print(child.tag, child.attrib)
	return ""
def getMacList(dom):
	raw_xml = dom.XMLDesc(0)
	xml = minidom.parseString(raw_xml)
	root = ET.fromstring(raw_xml)
	mac_addresses=[]
	interfaceTypes = xml.getElementsByTagName('interface')
	for interfaceType in interfaceTypes:
	#    print('interface: type='+interfaceType.getAttribute('type'))
	    interfaceNodes = interfaceType.childNodes
	    for interfaceNode in interfaceNodes:
		if interfaceNode.nodeName[0:1] != '#' and interfaceNode.nodeName == "mac":
		    for attr in interfaceNode.attributes.keys():
	#		print('mac '+interfaceNode.attributes[attr].name+' = '+ interfaceNode.attributes[attr].value)
			mac_addresses.append(interfaceNode.attributes[attr].value)
	return mac_addresses

def buildMacMap(mac_address, dom):
	try: 
		domainNameList = mapOfMacToDomainName[mac_address]
		domainNameList.append(dom.name())
		mapOfMacToDomainName[mac_address] = domainNameList 
	except:
		mapOfMacToDomainName[mac_address] = [dom.name()] 

def buildIpMap( mac_address , dom):
	try: 
		domainNameList = mapOfIpToDomainName[mac_address]
		domainNameList.append(dom.name())
		mapOfIpToDomainName[mac_address] = domainNameList 
	except:
		mapOfIpToDomainName[mac_address] = [dom.name()] 

def getipfrommac(dom , mac_addresses):
	for mac_address in mac_addresses:
	# Now, use subprocess to lookup that macaddress in the
	#      ARP tables of the host.
		process = subprocess.Popen(['/usr/sbin/arp', '-a'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		process.wait()  # Wait for it to finish with the command
		for line in process.stdout:
		    if mac_address in line:
			ip_address = re.search(r'(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})', line)
			print( dom.name(), mac_address, ip_address.groups(0)[0])
			buildMacMap(mac_address, dom)
			buildIpMap(mac_address , dom)

def getmacipinfo(domains):
	for domainID in domains:
		dom = conn.lookupByID(domainID)
		if dom == None:
		    print('Failed to find the domain '+domainID, file=sys.stderr)
		    exit(1)

		mac_addresses=getMacList(dom)
		getipfrommac(dom , mac_addresses)

def assignNextMac(mac_address):
	new_mac_address= mac_address
	while mapOfMacToDomainName[new_mac_address]:
		lastbyte = new_mac_address[ len(new_mac_address) - 2: ]
		hexlastbyte = "0x" + lastbyte
		if hexlastbyte == "0xff":
			hexlastbyte = "0x00"
		hex_int = int(hexlastbyte,16)
		new_int = hex(hex_int + 1)
		newlastbyte = str(new_int)
		strnewlastbyte = newlastbyte[2:]
		new_mac_address = new_mac_address[: len(new_mac_address) - 2] + strnewlastbyte
		try:
			vmlist = mapOfMacToDomainName[new_mac_address]
		except:
			break

	print("HASH complete");
	return new_mac_address

def resolveMacConflict():
	for key in mapOfMacToDomainName:
		vmlist=mapOfMacToDomainName[key]
		if len(vmlist) <= 1:
			continue
		for nextvm in range(1,len(vmlist)):
			new_mac_address = assignNextMac(key)
			mapOfMacToDomainName[new_mac_address] = [vmlist[nextvm]]


def resolveIpConflict():
	print(" TO DO ");
	
conn = libvirt.open('qemu:///system')
if conn == None:
    print('Failed to open connection to qemu:///system', file=sys.stderr)
    exit(1)

try:
	domains = conn.listDomainsID()
except :
	print("No domains !")
	sys.exit(1)

getmacipinfo(domains)

resolveMacConflict()
resolveIpConflict()
conn.close()
exit(0)
