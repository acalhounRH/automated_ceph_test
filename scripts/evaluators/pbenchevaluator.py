




class pbenchevaluator:


    def emit_actions():
                with open(pfname) as csvfile:
                    readCSV = csv.reader(csvfile, delimiter=',')
                    for row in readCSV:
                        if first_row:
                            col_num = len(row)
                            for col in range(col_num):
                                col_ary.append(row[col])
                                first_row = False
                        else:
                            for col in range(col_num):
                                if 'timestamp_ms' in col_ary[col]:
                                    ms = float(row[col])
                                    thistime = datetime.datetime.fromtimestamp(ms/1000.0)
                                    pbenchdoc['_source']['date'] = thistime.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                                else:
                                    if 'pidstat' in pbenchdoc['_source']['tool']:

                                        pname = col_ary[col].split('/')[-1]
                                        if "ceph-osd" in pname or "ceph-mon" in pname or "ceph-mgr" in pname:
                                            piddoc = copy.deepcopy(pbenchdoc)
                                            pid = col_ary[col].split('-', 1)[0]
                                            piddoc['_source']['process_name'] = pname
                                            piddoc['_source']['process_pid'] = pid
                                            piddoc['_source']['process_value'] = float(row[col])
                                            a = copy.deepcopy(piddoc)
                                    elif 'sar' in pbenchdoc['_source']['tool'] and "network_" in pbenchdoc['_source']['file_name']:
                                        sardoc = copy.deepcopy(pbenchdoc)
                                        sardoc['_source']['network_interface'] = col_ary[col]
                                        sardoc['_source']['network_value'] = float(row[col])
                                        a = copy.deepcopy(sardoc)
                                    elif 'sar' in pbenchdoc['_source']['tool'] and "memory_" in pbenchdoc['_source']['file_name']:
                                        sardoc = copy.deepcopy(pbenchdoc)
                                        sardoc['_source']['memory_stat'] = col_ary[col]
                                        sardoc['_source']['memory_value'] = float(row[col])
                                        a = copy.deepcopy(sardoc)
                                    #elif 'sar' in pbenchdoc['_source']['tool'] and "per_cpu_" in pbenchdoc['_source']['file_name']:
                                    #    sardoc = copy.deepcopy(pbenchdoc)
                                    #    sardoc['_source']['sarcpu_stat'] = col_ary[col]
                                    #    sardoc['_source']['sarcpu_value'] = float(row[col])
                                    #    a = copy.deepcopy(sardoc)
                                    elif 'iostat' in pbenchdoc['_source']['tool']:
                                        iostatdoc = copy.deepcopy(pbenchdoc)
                                        iostatdoc['_source']['device'] = col_ary[col]
                                        iostatdoc['_source']['iostat_value'] = float(row[col])
                                        a = copy.deepcopy(iostatdoc)
                                    elif 'mpstat' in pbenchdoc['_source']['tool'] and "cpuall_cpuall.csv" in pbenchdoc['_source']['file_name']:
                                        mpstat = copy.deepcopy(pbenchdoc)
                                        mpstat['_source']['cpu_stat'] = col_ary[col]
                                        mpstat['_source']['cpu_value'] = float(row[col])
                                        a = copy.deepcopy(mpstat)
                                if a:
                                        #XXX:TODO
                                        actions.append(a) #change to yield a
                                        index = True

