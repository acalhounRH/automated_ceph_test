from scribes import *
import cbt_pbench_analyzer
import cbt_fio_analyzer
import cbt_rados_analyzer
import logging

logger = logging.getLogger("index_cbt")

_analyzer_mapping = {"librbdfio" : cbt_fio_analyzer.analyze_cbt_fio_results,
                          "rados": cbt_rados_analyzer.analyze_cbt_rados_results}

class analyzer_factory():
        
    @staticmethod
    def factory(self, benchmark_name, dirpath, cbt_config_gen, test_metadata, type):
        try:
            logger.debug(benchmark_name)
            logger.debug("")
            logger.debug(dirpath, cbt_config_gen, test_metadata, type)
            
            for i in args:
                print i
                
            for i in kwargs:
                print i
            return _analyzer_mapping[args](dirpath, cbt_config_gen, test_metadata, type)
        except KeyError:
            raise FactoryError(benchmark_name, "Unkown benchmark")
            
        
    def register(self, benchmark_name, analyzer_object):
        _analyzer_mapping[benchmark_name] = analyzer_object