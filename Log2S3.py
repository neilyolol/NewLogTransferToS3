"""
Author Chao Yuan
From 2015/2/9
"""

from __future__ import print_function,with_statement,absolute_import
import fabric.api
from fabric.decorators import *
from fabric.context_managers import *
from pyzabbix import ZabbixAPI
import requests,argparse,ConfigParser,os

ZABBIX_SERVER = 'http://ec2-zabbixserver-01.ec2.mypna.com/zabbix'
zapi = ZabbixAPI(ZABBIX_SERVER)
zapi.login('rpc', 'mypna123')

env.skip_bad_hosts = True
env.keepalive = 60

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    BOLD = "\033[1m"
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

    def disable(self):
        self.HEADER = ''
        self.OKBLUE = ''
        self.OKGREEN = ''
        self.BOLD = ""
        self.WARNING = ''
        self.FAIL = ''
        self.ENDC = ''

#Mark IRC message
def irc_mark(nickname,message):
        url = '''http://telenav-irc.telenav.com:8081/IRC_Requests/?nick=''' + nickname + '''&msg=''' + message
        r = requests.get(url)

#Get instances from Zabbix
def get_cluster_instances_oregon(cluster_name):
    """
    Try to get cluster instances from zabbix located at Oregon
    :param cluster_name: such as entitysvc or sth else
    :return: instance list from Zabbix
    """
    groupids_oregon = retrieve_hostgroup('EC2-OR')
    filtered_hosts_oregon = retrieve_host_with_groupid(groupids_oregon, cluster_name)
    assert isinstance(filtered_hosts_oregon, object)
    return filtered_hosts_oregon

def get_cluster_instances_virginia(cluster_name):
    """
    Try to get cluster instances from zabbix located at virginia
    :param cluster_name: such as entitysvc or sth else
    :return: instance list from Zabbix
    """
    groupids_virginia = retrieve_hostgroup('EC2-VA')
    filtered_hosts_virginia = retrieve_host_with_groupid(groupids_virginia,cluster_name)
    assert isinstance(filtered_hosts_virginia, object)
    return filtered_hosts_virginia

def log_user():
    """
    Try to find out which user recorded the logs
    :return: log user list
    """
    java_user = run("ps -ef|grep java|grep -v `whoami`|awk '{print $1}'")
    return list(set(java_user.split('\r\n')))

def catalina_home():
    command = ''' ps -fC java --noheaders|awk '{for (i=1;i<=NF;i++) { if ( $i ~ /Dcatalina.home/ ) {split($i,x,"=");print x[2]}}}' '''
    return run(command).splitlines()

def home_log_dir(user):
    path = "/home/" + user + "/"
    command = "find" + path + " \( -type d -o -type l \) -name '*log*' -print 2>/dev/null"
    return sudo(command,user=user).splitlines()








