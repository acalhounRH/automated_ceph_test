#!/bin/bash

inventory_file=$1

for host in `ansible --list-host all -i $inventory_file | grep -vi host`
do
  new_config="
  Host $host
    User root
    StrictHostKeyChecking no
  "

  echo "$new_config" >> $HOME/.ssh/config
done


