#! /usr/bin/python

import os

from linode import LinodeClient
client = LinodeClient(os.environ['LINODE_API_KEY'])

my_linodes = client.linode.get_instances()

for current_linode in my_linodes:
    print(current_linode.label)


DC_ID = 6 # Newark, NJ
PLAN_ID = 1 # 1024
DISTRIBUTION_ID = "CentOS 7" #129


available_regions = client.get_regions()
available_images = client.get_images()
available_types = client.linode.get_types()

for i in available_regions:    
    print i

for i in available_images:
    print i

for i in available_types:
    print i

chosen_region = available_regions[3]
chosen_image = available_images[3]

#new_linode, password = client.linode.create_instance(region='us_east', type='g6-nanode-1', image='linode/centos7')




ltype = client.linode.get_types().first()
region = client.get_regions().first()
image = client.get_images().first()
another_linode, password = client.linode.create_instance(
               ltype,
               region,
               image=image)

#new_linode, password = client.linode.create_instance(6,
#                                                     1,
#                                                     image='linode/centos7')

print("ssh root@{} - {}".format(another_linode.ipv4[0], password))
