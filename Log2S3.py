"""
Author Chao Yuan
From 2015/2/9
"""

from __future__ import print_function, with_statement
from fabric.api import run, env, sudo, execute, local
from fabric.decorators import *
from fabric.context_managers import *
from pyzabbix import ZabbixAPI
import requests, argparse, ConfigParser, os

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


# Mark IRC message
def irc_mark(nickname, message):
    url = '''http://telenav-irc.telenav.com:8081/IRC_Requests/?nick=''' + nickname + '''&msg=''' + message
    r = requests.get(url)


# Get instances from Zabbix
def retrieve_hostgroup(group_name_list):
    groupids = zapi.hostgroup.get(
        output=['groupid'],
        filter={
            'name': group_name_list
        }
    )
    return [each_item['groupid'] for each_item in groupids]


def retrieve_host_with_groupid(groupids, cluster_name):
    hosts = zapi.host.get(
        output=['hosts'],
        groupids=groupids,
        filter={
            'status': 0
        },
        search={
            'host': '-' + cluster_name + '-'
        }
    )
    return [each['host'] for each in hosts]


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
    filtered_hosts_virginia = retrieve_host_with_groupid(groupids_virginia, cluster_name)
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
    return sudo(command, user=user).splitlines()


def all_log_directories():
    global loguser, all_catalina_dir, all_userlog_dir, all_log_dir
    loguser = log_user()
    all_log_dir = []
    for each_dir in catalina_home():
        all_catalina_dir += " " + each_dir + "/logs/"
    for each_user in loguser:
        userid = run("id -u" + each_user)
        for each_dir in home_log_dir(each_user):
            all_userlog_dir = all_userlog_dir + " " + each_dir + "/"
        command_b = "find" + all_userlog_dir + " " + all_catalina_dir + " -maxdepth 3 -type f \( -name '*.gz' -a -name '*-??-* \) " + " -user " + userid + ''' -print|awk -F / 'Begin{OFS="/"}{$NF="";print}'|uniq '''
        all_log_dir.extend(run(command_b).splitlines())
    all_log_dir = list(set(all_log_dir))


def upload_to_s3():
    s3_prefix_oregon = 's3://noc-archive-oregon/logs/'
    s3_prefix_virginia = 's3://noc-archive-east/logs/'
    host_string = local('echo' + env.host_string + ''' |awk -F. '{print $1}' ''', capture=True)
    domain_string = local('echo' + env.host_string + ''' |awk -F- '{print $1}' ''', capture=True)
    cluster_name = local('echo ' + env.host_string + ''' |awk -F- '{print $2}' ''', capture=True)
    all_log_directories()
    for each_log_dir in all_log_dir:
        

    irc_mark('Logtransfer', 'Start upload logs ')








