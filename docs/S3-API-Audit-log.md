---
id: S3-API-Audit-log
title: "S3 API Audit log"
sidebar_label: "S3 API Audit log"
---

### How do I enable log delivery?

```weed s3 -auditLogConfig=/etc/seaweedfs/auditLogConfig.json```

#### Example config defaults:
```
{
    "fluent_port": 24224,
    "fluent_host": "127.0.0.1",
    "fluent_network": "tcp",
    "timeout": 3000,
    "write_timeout": 0,
    "buffer_limit": 8192,
    "retry_wait": 500,
    "max_retry": 13,
    "max_retry_wait": 60000,
    "tag_prefix": ""
}
```

### Access log format

```
{"requester":"bennu","host_id":"api-698ccd9645-sccv6","status":200,"time":1639395995,"operation":"REST.PUT.OBJECT","remote_ip":"10.106.70.45","signature_version":"SigV4","bucket":"bennu-files","user_agent":"Python/3.8 aiohttp/3.6.2","key":"/2021/12/13/a029a35d-b73c-42f1-9540-7f0370a17f7c","request_id":"c89f2a45eebc63f2b01aca823a1f6cba","host_header":"bennu-files.s3-proxy.svc","error_code":""}
{"requester":"bennu","host_id":"api-698ccd9645-g8fht","status":200,"time":1639395992,"operation":"REST.GET.OBJECT","remote_ip":"10.106.70.45","signature_version":"SigV4","bucket":"bennu-files","user_agent":"Python/3.8 aiohttp/3.6.2","key":"/2021/12/13/69f82cd8-ff31-476d-aa53-5e1e2109b84c","request_id":"570ceb8d3b8c31d51070910a78b26045","host_header":"bennu-files.s3-proxy.svc","error_code":""}
```

### How to ingest log ?

#### Fluent

#### Logstash

logstash.conf:
```
filter {
  if [tags][0] and [tags][0] =~ /s3.access/ {
    ruby {
      code => 'event.set("environment", ((event.get("tags").first).split(".")).first)'
      add_field  => { "[@metadata][input_type]" => "s3.access" }
      remove_field => [ host, "@timestamp", "@version", port, tags ]
    }
  }
  if ![environment] or [environment] == "" {
      mutate {
        replace => { "environment" => "unknown" }
      }
  }
}
input {
  tcp {
    codec => fluent
    port => 24224
  }
}
output {
  if [@metadata][input_type] == "s3.access" {
    clickhouse {
      headers => ["Authorization", "Basic ${CLICKHOUSE_BASIC_AUTH}"]
      http_hosts => ["${CLICKHOUSE_URL}", "${CLICKHOUSE_URL}"]
      table => "${CLICKHOUSE_TABLE}"
      flush_size => 1000
      pool_max => 1000
      idle_flush_time => 5
      backoff_time => 3
      request_tolerance => 5
      automatic_retries => 1
      save_on_failure => true
      save_dir => "${CLICKHOUSE_SAVE_DIR}"
      date_time_input_format => "best_effort"
      skip_unknown => "1"
      id => "clickhouse"
    }
  }
}
```




```
