from datetime import timedelta
import datetime
import uuid
import boto
from boto.ec2.connection import EC2Connection
from boto.regioninfo import RegionInfo, RegionInfo
import os
import cloudboot
from cloudboot.exceptions import ConfigException, IaaSException
import time

__author__ = 'bresnaha'


g_fake_instance_table = {}

class IaaSTestCon(object):
    def __init__(self):
        pass

class IaaSTestInstance(object):

    def __init__(self, hostname, time_to_hostname=2.0):
        global g_fake_instance_table

        self.public_dns_name = None
        self.state = "pending"
        
        self._hostname = hostname
        self.id = str(uuid.uuid4()).split('-')[0]
        g_fake_instance_table[self.id] = self

        self.time_to_hostname = time_to_hostname
        self._time_next_state = datetime.datetime.now() + timedelta(days=0, seconds=time_to_hostname)
        self._next_state = "running"

    def terminate(self):
        self._time_next_state = datetime.datetime.now() + timedelta(days=0, seconds=self.time_to_hostname)
        self._next_state = "running"
        self.state = "shutting-down"

    def update(self):
        now = datetime.datetime.now()
        if self._time_next_state and self._next_state and now > self._time_next_state:
            self.state = self._next_state
            self.public_dns_name = self._hostname
            self._next_state = None
            self._time_next_state = None
        return self.state

def iaas_find_instance(con, instance_id):
    global g_fake_instance_table

    if type(con) == IaaSTestCon:
        return g_fake_instance_table[instance_id]
    else:
        return _real_find_instance(con, instance_id)

def iaas_get_con(key, secret, iaashostname=None, iaasport=None):
    if 'CLOUDBOOT_TESTENV' in os.environ:
        return IaaSTestCon()
    else:
        return _real_iaas_get_con(key, secret, iaashostname, iaasport)

def iaas_run_instance(con, image, instance_type, key_name, security_groupname=None):
    if type(con) == IaaSTestCon:
        h = str(uuid.uuid1()) + ".nimbusproject.org"
        return IaaSTestInstance(h)
    else:
        return _real_iaas_run_instance(con, image, instance_type, key_name, security_groupname)
        
def _real_iaas_get_con(key, secret, iaashostname=None, iaasport=None):

    orig_key = key
    orig_secret = secret
    # look up key and secret in env if needed
    key = cloudboot.get_env_val(key)
    secret = cloudboot.get_env_val(secret)
    if not key:
        raise ConfigException("IaaS key %s not in env" % (orig_key))
    if not secret:
        raise ConfigException("IaaS key %s not in env" % (orig_secret))
    # see comments in validate()
    if not iaashostname:
        con = EC2Connection(key, secret)
    else:
        region = RegionInfo(iaashostname)
        if not iaasport:
            con =  boto.connect_ec2(key, secret, region=region)
        else:
            con =  boto.connect_ec2(key, secret, port=iaasport, region=region)

    return con

def _real_iaas_run_instance(con, image, instance_type, key_name, security_groupname=None):
    sec_group = None
    if security_groupname:
         sec_group_a = con.get_all_security_groups(groupnames=[security_groupname,])
         sec_group = sec_group_a[0]

    reservation = con.run_instances(image, instance_type=instance_type, key_name=key_name, security_groups=sec_group)
    instance = reservation.instances[0]
    return instance

def _real_find_instance(con, instance_id):
    reservation = con.get_all_instances(instance_ids=[instance_id,])
    if len(reservation) < 1:
        raise IaaSException(Exception("There is no instance %s" % (instance_id)))
    if len(reservation[0].instances) < 1:
        ex = IaaSException(Exception("There is no instance %s" % (instance_id)))
        print ex
        raise ex
    instance = reservation[0].instances[0]

    return instance