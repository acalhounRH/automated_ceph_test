pipeline {
    agent {label 'master'}
        stages {
            stage('Build') {
            	when {
            		environment name: 'Deploy', value: 'true'
            		}
                steps {
                    build job: '1A-Push_SW_To_Remote_Agent', parameters: [
                        string(name: 'ceph_iso_file', value: "$iso_file"),
                        string(name: 'ceph_iso_path', value: "$iso_path"),
                        string(name: 'version_adjust_repo', value:"$version_adjust_repo"),
                        string(name: 'agentname', value: "$node")]
                    build job: '1-Deploy_Ceph_Cluster', parameters: [
                        password(description: 'Linode API Key', name: 'linode_api_key', value: "$linode_api_key"),
                        text(name: 'Linode_Cluster_Configuration', value: "$Linode_Cluster_Configuration"),
                        text(name: 'ceph_inventory', value: "$ceph_inventory"),
                        string(name: 'ceph_iso_file', value: "$iso_file"),
                        string(name: 'ceph_iso_path', value: "$iso_path"),
                        string(name: 'version_adjust_repo', value:"$version_adjust_repo"),
                        string(name: 'ansible_version', value:"$ansible_version"),
                        text(name: 'ceph_ansible_all_config', value: "$all_config"),
                        text(name: 'ceph_ansible_osds_config', value: "$osds_config"),
                        [$class: 'NodeParameterValue', name: 'agentName', labels: ["$node"], , nodeEligibility: [$class: 'AllNodeEligibility']]]
                    }
            }
            stage('Test Setup') {
                steps {
                    build job: '2-Setup_Test_Tools', parameters: [
                        booleanParam(name: 'linode_cluster', value: false),
                        booleanParam(name: 'sar', value: Boolean.valueOf(sar)),
                        string(name: 'sar_interval', value: "$sar_interval"),
                        booleanParam(name: 'iostat', value: Boolean.valueOf(iostat)),
                        string(name: 'iostat_interval', value: "$iostat_interval"),
                        booleanParam(name: 'mpstat', value: Boolean.valueOf(mpstat)),
                        string(name: 'mpstat_interval', value: "$mpstat_interval"),
                        booleanParam(name: 'pidstat', value: Boolean.valueOf(pidstat)),
                        string(name: 'pidstat_interval', value: "$pidstat_interval"),
                        booleanParam(name: 'proc-vmstat', value: Boolean.valueOf(proc_vmstat)),
                        string(name: 'proc-vmstat_interval', value: "$proc_vmstat_interval"),
                        booleanParam(name: 'proc-interrupts', value: Boolean.valueOf(proc_interrupts)),
                        string(name: 'proc-interrupts_interval', value: "$proc_interrupts_interval"),
                        booleanParam(name: 'turbostat', value: Boolean.valueOf(turbostat)),
                        string(name: 'turbostat_interval', value: "$turbostat_interval"),
                        [$class: 'NodeParameterValue', name: 'agentName', labels: ["$node"], , nodeEligibility: [$class: 'AllNodeEligibility']]]
                    }
            }
            stage('Test') {
                steps {
                
               		env.starttime = currentBuild.getTimeInMillis()

                	
                    build job: '3-CBT_Automated_Testing', parameters: [
                        booleanParam(name: 'linode_cluster', value: false),
                        string(name: 'cbt_archive_dir', value: "/var/lib/pbench-agent/$Test_ID"),
                        text(name: 'cbt_settings', value: "$settings"),
                        [$class: 'NodeParameterValue', name: 'agentName', labels: ["$node"], , nodeEligibility: [$class: 'AllNodeEligibility']]]
                        
                	env.stoptime = currentBuild.getTimeInMillis()
                }
            }
            stage('Analysis') {
                steps{
                    build job: '4-Perform_Analysis', parameters: [
                        string(name: 'Test_ID', value: "$Test_ID"),
                        string(name: 'archive_dir', value: "/var/lib/pbench-agent/$Test_ID"),
                        string(name: 'elasticsearch_host', value: 'localhost'),
                        string(name: 'elasticsearch_port', value: '9200'),
                        [$class: 'NodeParameterValue', name: 'agentName', labels: ["$node"], , nodeEligibility: [$class: 'AllNodeEligibility']]]
                    }
            }
            stage('Teardown') {
            	when {
            		environment name: 'Teardown', value: 'true'
            	}
            	steps{
                	build job:'5-Teardown_Ceph_Cluster', parameters: [
                    	password(description: 'Linode API Key', name: 'Linode_API_Key', value: "$Linode_API_Key"), 
                    	string(name: 'teardown_delay_minutes', value: "$teardown_delay_minutes"), 
                    	text(name: 'preexisting_ansible_inventory', value: "$ceph_inventory"),
                    	[$class: 'NodeParameterValue', name: 'agentName', labels: ["$node"], nodeEligibility: [$class: 'AllNodeEligibility']]]
               	}
            }
        }
        post {
            success {
                node ('master') {
                    emailext 
                    body: " ${currentBuild.currentResult}: Job ${env.JOB_NAME} build ${env.BUILD_NUMBER}\n More info at: ${env.BUILD_URL}\n Visualization of results can be found ${here, path="http://famine.perf.lab.eng.bos.redhat.com:3000/d/wXlLG4hik/rbd-experimental-dashboards?orgId=1&from=${env.starttime}&to=${env.stoptime}&var-Test_ID=${Test_ID}&var-time_interval=\$__auto_interval_time_interval&var-Operation=All&var-object_size=All"}",
            		recipientProviders:[[$class: 'RequesterRecipientProvider']],
            		subject: "Jenkins Build ${currentBuild.currentResult}: Job ${env.JOB_NAME}"
                }
                        
            }
            failure {
                node ('master') {
                    mail to: 'acalhoun@redhat.com',
                    subject: "Failed Pipeline: ${currentBuild.fullDisplayName}",
                    body: "Something is wrong with ${env.BUILD_URL}"
                }
            }
        }
}
