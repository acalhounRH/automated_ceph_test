import binascii
import logging
import os
import errno
import sys

from multiprocessing.dummy import Pool as ThreadPool

from contextlib import closing

from linode_api4 import LinodeClient

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')

GROUP = "Jenkins"

def main():
    agent_label = os.environ['AGENT_NAME'] 
    key = os.getenv("LINODE_API_KEY")
    if key is None:
        raise RuntimeError("please specify Linode API key")

    client = LinodeClient(key)

    def destroy(linode):
        linode.delete()
        #client.linode_delete(LinodeID = linode[u'LINODEID'], skipChecks = 1)

    linodes = client.linode.instances()
    #logging.info("linodes: {}".format(linodes))

    with closing(ThreadPool(5)) as pool:
        agent = filter(lambda linode: linode.label == agent_label, linodes)
        pool.map(destroy, agent)
        pool.close()
        pool.join()

if __name__ == "__main__":
    main()
