"""Dictionary of technologies and certifications the radar looks for in job ads.

Each entry: key -> (display name, [regex patterns], weight).
Certifications get a lower weight so a missing cert hurts the score less
than a missing hands-on skill. Keys are what you reference in config/profile.yml.
"""

SKILLS = {
    # Cloud
    "aws": ("AWS", [r"\baws\b", r"amazon web services", r"\bec2\b", r"\bcloudwatch\b"], 1.0),
    "azure": ("Azure", [r"\bazure\b"], 1.0),
    "gcp": ("GCP", [r"\bgcp\b", r"google cloud"], 1.0),
    "openstack": ("OpenStack", [r"\bopenstack\b"], 1.0),
    "serverless": ("Serverless / Lambda", [r"serverless", r"\blambda\b", r"cloud functions"], 1.0),
    # Containers and orchestration
    "docker": ("Docker", [r"\bdocker\b", r"\bcontaineri[sz]", r"\bpodman\b"], 1.0),
    "kubernetes": ("Kubernetes", [r"\bkubernetes\b", r"\bk8s\b", r"\beks\b", r"\baks\b", r"\bgke\b"], 1.0),
    "openshift": ("OpenShift", [r"\bopenshift\b"], 1.0),
    "helm": ("Helm", [r"\bhelm\b"], 1.0),
    "istio": ("Service mesh (Istio)", [r"\bistio\b", r"service mesh", r"\blinkerd\b"], 1.0),
    # IaC and config management
    "terraform": ("Terraform", [r"\bterraform\b", r"\bopentofu\b"], 1.0),
    "cloudformation": ("CloudFormation", [r"cloudformation"], 1.0),
    "pulumi": ("Pulumi", [r"\bpulumi\b"], 1.0),
    "ansible": ("Ansible", [r"\bansible\b"], 1.0),
    "puppet": ("Puppet", [r"\bpuppet\b"], 1.0),
    "saltstack": ("SaltStack", [r"\bsalt ?stack\b"], 1.0),
    # CI/CD
    "cicd": ("CI/CD", [r"\bci ?/ ?cd\b", r"continuous (?:integration|delivery|deployment)"], 1.0),
    "jenkins": ("Jenkins", [r"\bjenkins\b"], 1.0),
    "gitlab_ci": ("GitLab CI", [r"gitlab[- ]?ci", r"gitlab pipelines?"], 1.0),
    "github_actions": ("GitHub Actions", [r"github actions"], 1.0),
    "argocd": ("Argo CD / GitOps", [r"argo ?cd", r"\bgitops\b", r"\bflux ?cd\b"], 1.0),
    "git": ("Git", [r"\bgit\b", r"\bgithub\b", r"\bbitbucket\b"], 1.0),
    # Scripting
    "python": ("Python", [r"\bpython\b"], 1.0),
    "bash": ("Bash / Shell", [r"\bbash\b", r"shell script"], 1.0),
    "powershell": ("PowerShell", [r"powershell"], 1.0),
    "golang": ("Go", [r"\bgolang\b", r"(?-i:\bGo\b)(?=\s*(?:[,/)]|or\b|and\b|for\b))", r"(?:python|java|rust|bash) or (?-i:Go)\b"], 1.0),
    # Operating systems
    "linux": ("Linux", [r"\blinux\b", r"\bunix\b", r"\bubuntu\b", r"\bdebian\b", r"\bcentos\b"], 1.0),
    "rhel": ("RHEL", [r"\brhel\b", r"red ?hat"], 1.0),
    "suse": ("SUSE", [r"\bsuse\b", r"\bsles\b"], 1.0),
    "windows_server": ("Windows Server", [r"windows server", r"\bwindows\b(?= (?:server|administration|environments?|infrastructure))"], 1.0),
    "active_directory": ("Active Directory", [r"active directory", r"\bentra id\b", r"\bazure ad\b", r"\bgpo\b"], 1.0),
    "m365": ("Microsoft 365 / Exchange", [r"microsoft 365", r"office 365", r"\bo365\b", r"\bm365\b", r"\bintune\b", r"\bexchange server\b"], 1.0),
    # Virtualization
    "vmware": ("VMware vSphere", [r"\bvmware\b", r"\bvsphere\b", r"\bvcenter\b", r"\besxi\b", r"\bvsan\b", r"\bnsx"], 1.0),
    "proxmox": ("Proxmox", [r"\bproxmox\b"], 1.0),
    "hyperv": ("Hyper-V", [r"hyper-?v\b"], 1.0),
    "nutanix": ("Nutanix", [r"\bnutanix\b"], 1.0),
    "virtualization": ("Virtualization", [r"virtuali[sz]ation"], 1.0),
    "ha_clustering": ("High availability / clustering", [r"high[- ]availability", r"\bpacemaker\b", r"\bfailover\b", r"\bclustering\b"], 1.0),
    # Observability
    "prometheus": ("Prometheus", [r"\bprometheus\b"], 1.0),
    "grafana": ("Grafana", [r"\bgrafana\b"], 1.0),
    "zabbix": ("Zabbix", [r"\bzabbix\b"], 1.0),
    "nagios": ("Nagios / Icinga", [r"\bnagios\b", r"\bicinga\b"], 1.0),
    "elk": ("ELK / OpenSearch", [r"\belk\b", r"elasticsearch", r"\bkibana\b", r"logstash", r"opensearch"], 1.0),
    "datadog": ("Datadog", [r"\bdatadog\b"], 1.0),
    "splunk": ("Splunk", [r"\bsplunk\b"], 1.0),
    "incident": ("Incident response / on-call", [r"incident (?:management|response)", r"\bon-?call\b", r"\bslos?\b", r"error budgets?"], 1.0),
    # Web servers and load balancing
    "nginx": ("Nginx", [r"\bnginx\b"], 1.0),
    "haproxy": ("HAProxy / load balancing", [r"\bhaproxy\b", r"keepalived", r"load[- ]balanc"], 1.0),
    "apache": ("Apache HTTPD", [r"\bapache\b(?! (?:kafka|spark|airflow|flink|cassandra|beam))"], 1.0),
    "iis": ("IIS", [r"\biis\b"], 1.0),
    # Data stores and messaging
    "mysql": ("MySQL / MariaDB", [r"\bmysql\b", r"\bmariadb\b"], 1.0),
    "postgresql": ("PostgreSQL", [r"postgres"], 1.0),
    "mongodb": ("MongoDB", [r"\bmongo"], 1.0),
    "redis": ("Redis", [r"\bredis\b"], 1.0),
    "sql_server": ("SQL Server", [r"sql server", r"\bmssql\b"], 1.0),
    "oracle_db": ("Oracle DB", [r"\boracle\b(?! cloud)"], 1.0),
    "kafka": ("Kafka", [r"\bkafka\b"], 1.0),
    "rabbitmq": ("RabbitMQ", [r"rabbitmq"], 1.0),
    "sap_hana": ("SAP HANA", [r"\bhana\b"], 1.0),
    "sap_basis": ("SAP Basis", [r"sap basis", r"\bbasis (?:admin|administrator|consultant|engineer)"], 1.0),
    # Networking, security, backup, storage
    "networking": ("Networking (TCP/IP, DNS, VLANs)", [r"tcp/ip", r"\bdns\b", r"\bdhcp\b", r"\bvlans?\b", r"\bbgp\b", r"\bospf\b", r"\bnetworking\b", r"\bccna\b", r"\bvpns?\b"], 1.0),
    "firewalls": ("Firewalls", [r"firewall", r"fortinet", r"fortigate", r"palo alto", r"pfsense", r"opnsense", r"check ?point"], 1.0),
    "cisco": ("Cisco", [r"\bcisco\b"], 1.0),
    "vault": ("HashiCorp Vault / secrets", [r"\bvault\b", r"secrets management"], 1.0),
    "devsecops": ("Security scanning (DevSecOps)", [r"devsecops", r"\btrivy\b", r"\bsnyk\b", r"sonarqube", r"\bsast\b", r"\bdast\b"], 1.0),
    "veeam": ("Veeam", [r"\bveeam\b"], 1.0),
    "backup_dr": ("Backup and disaster recovery", [r"\bbackups?\b", r"disaster recovery", r"\bbcdr\b"], 1.0),
    "storage": ("Storage (SAN/NAS/Ceph)", [r"\bsan\b", r"\bnas\b", r"\bnetapp\b", r"\bceph\b", r"storage (?:systems|administration|arrays?)"], 1.0),
    # Certifications (lower weight)
    "cert_k8s": ("CKA / CKAD", [r"\bcka\b", r"\bckad\b", r"\bcks\b", r"certified kubernetes"], 0.5),
    "cert_aws": ("AWS certification", [r"aws certifi", r"aws (?:solutions architect|sysops|devops engineer)[ -]+(?:associate|professional)"], 0.5),
    "cert_azure": ("Azure certification (AZ-104…)", [r"\baz-\d{3}\b", r"azure (?:administrator|solutions architect|devops engineer) (?:associate|expert)"], 0.5),
    "cert_gcp": ("Google Cloud certification", [r"google cloud certified", r"associate cloud engineer", r"professional cloud architect"], 0.5),
    "cert_redhat": ("RHCSA / RHCE", [r"\brhcsa\b", r"\brhce\b", r"red hat certified"], 0.5),
    "cert_terraform": ("Terraform Associate", [r"terraform associate", r"hashicorp certified"], 0.5),
    "cert_vmware": ("VMware VCP", [r"\bvcp\b", r"vmware certified"], 0.5),
}
