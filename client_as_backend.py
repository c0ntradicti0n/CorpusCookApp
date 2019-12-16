import glob
import logging
logging.getLogger().setLevel(logging.INFO)

from py4j.java_gateway import JavaGateway, CallbackServerParameters, GatewayParameters

import config
from config import htmls


class PythonInterface(object):
    def getHTMLpaths(self):
        logging.info("get html paths")
        paths =  list(glob.iglob(htmls + '/*.html', recursive=config.recursive))
        return self.new_java_list(paths)

    def new_java_list(self, list):
        java_list = self.gateway.jvm.java.util.ArrayList()
        for e in list:
            java_list.append(e)
        return java_list
    def pythonShutdown(self):
        logging.info("shut down")
        # and do resurrection
        self.gateway.shutdown()
        self.gateway = self._create_new_gateway()
        return None
    def __init__(self):
        logging.info("init ")
        self.gateway = self._create_new_gateway()
    def _create_new_gateway(self):
        logging.info("new gateway")
        return JavaGateway(
            callback_server_parameters=CallbackServerParameters(
                      daemonize_connections=True,       eager_load=True
            ),
            python_server_entry_point=self,
            gateway_parameters=GatewayParameters(auto_convert=True,

                                                 auto_close=True))
    class Java:
        implements = ["me.cc.pynterface.PythonInterface"]


pynterface = PythonInterface()

