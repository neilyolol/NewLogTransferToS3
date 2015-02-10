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


def upload_process(s3_upload_path):
    """

    :rtype : object
    """
    filename_command = " find ./ -maxdepth 1 -type f -name '*.gz' -exec ls -al  {} \; |awk '{print $9}'|awk -F/ '{print $2}' "
    file_to_sent = [run(filename_command).splitlines]
    for i in range(len(file_to_sent)):
        d = {file_to_sent[i]: run("ls -al " + file_to_sent[i] + "|awk '{print $5}' ")}
        run('s3cmd put ' + file_to_sent[i] + ' ' + s3_upload_path)
        file_size = run("s3cmd ls " + s3_upload_path + file_to_sent[i] + "|awk '{print $3}'")
        if str(file_size) == str(d[file_to_sent[i]]):
            run('rm -f ' + file_to_sent[i])
        else:
            print(file_to_sent[i] + " upload failed . Please check !")


def upload_to_s3():
    s3_prefix_oregon = 's3://noc-archive-oregon/logs/'
    s3_prefix_virginia = 's3://noc-archive-east/logs/'
    host_string = local('echo' + env.host_string + ''' |awk -F. '{print $1}' ''', capture=True)
    domain_string = local('echo' + env.host_string + ''' |awk -F- '{print $1}' ''', capture=True)
    cluster_name = local('echo ' + env.host_string + ''' |awk -F- '{print $2}' ''', capture=True)
    all_log_directories()
    for each_log_dir in all_log_dir:
        if domain_string == 'ec1':
            with cd(each_log_dir):
                s3_upload_path = s3_prefix_virginia + cluster_name + '/' + host_string + each_log_dir
                irc_mark('Logtransfer', 'Start upload logs from ' + host_string)
                upload_process(s3_upload_path)
        elif domain_string == 'ec2':
            with cd(each_log_dir):
                s3_upload_path = s3_prefix_oregon + cluster_name + '/' + host_string + each_log_dir
                upload_process(s3_upload_path)
                irc_mark('Logtransfer', 'Start upload logs from ' + host_string)

def job_4_config(config):
    for each_cluster in config.options():
        hosts = []
        hosts.extend(get_cluster_instances_oregon())
        hosts.extend(get_cluster_instances_virginia())
        if env.hosts:
            execute(upload_to_s3())

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Transfer all zipped log file from TeleNav AWS Virginia and Oregon servers to S3')
    parser.add_argument(
        'hosts',
        type=str,
        nargs='*',
        help='Hosts on which logs need to be transferred. '
    )
    parser.add_argument(
        '-f',
        '--config-file',
        nargs='?',
        dest='config_file',
        type=argparse.FileType('r'),
    )
    args = parser.parse_args()


    if args.config_file:
        config = ConfigParser.ConfigParser(allow_no_value=True)
        config.readfp(args.config_file)
        job_4_config(config)
        irc_mark('LogTransfer','[Completed]')







