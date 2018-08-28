

class fiologevaluator:

    def emit_actions(csv, json, metadata):
        jsondoc = json.load(open(jsonfile))
        test_time_ms = long(jsondoc['timestamp_ms'])
        test_duration_ms = long(jsondoc['global options']['runtime']) * 1000
        start_time = test_time_ms - test_duration_ms
    
        fiologdoc["_source"]['file'] = os.path.basename(file)
        with open(file) as csvfile:
            readCSV = csv.reader(csvfile, delimiter=',')
            for row in (readCSV):
                ms = float(row[0]) + float(start_time)
                newtime = datetime.datetime.fromtimestamp(ms/1000.0)
                fiologdoc["_source"]['date'] = newtime.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                fiologdoc["_source"]['value'] = int(row[1])
                fiologdoc["_source"]['data direction'] = row[2]
                #print json.dumps(fiologdoc, indent=1)
                a = copy.deepcopy(fiologdoc)
                actions.append(a) #XXX: TODO change to yield a
