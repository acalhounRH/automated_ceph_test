
class fiojson_evaluator:

    __init__()

    def emit_actions(json_file, metadata):
        importdoc = {}
        header = {}
        importdoc['header'] = {}

        json_doc = json.load(open(json_file))
        #create header dict based on top level objects
        importdoc['date'] = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.localtime(doc['timestamp']))
        importdoc['header']['global_options'] = json_doc['global options']
        importdoc['header']['global_options']['bs'] = ( int(importdoc['header']['global_options']['bs'].strip('B')) / 1024)
        importdoc['header']['timestamp_ms'] = json_doc['timestamp_ms']
        importdoc['header']['timestamp'] = json_doc['timestamp']
        importdoc['header']['fio_version'] = json_doc['fio version']
        importdoc['header']['time'] = json_doc['time']
        importdoc['header']['iteration'] = iteration
        importdoc['header']['test_id'] = test_id
        for job in json_doc['jobs']:
            importdoc['job'] = job
            yield importdoc 
            res = es.index(index="fio3-index", doc_type='fiojson', body=importdoc)
