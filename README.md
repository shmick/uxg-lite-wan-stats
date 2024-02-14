
### Since I'm using PPPoE with my ISP, I'm monitoring the ppp0 interface

### The script to gather stats and send them to Home Assistant. This gets installed on the UXG Lite 

#### Filename: /persistent/system/ppp0_stats.sh
```bash
#!/bin/bash

# Get Receive and Transmit bytes for ppp0 interface
if read data_received data_sent < <(awk '/ppp0:/{print $2, $10}' /proc/net/dev); then
    # Validate that data_received and data_sent are numbers
    if [[ ! "$data_received" =~ ^[0-9]+$ ]] || [[ ! "$data_sent" =~ ^[0-9]+$ ]]; then
        echo "Error: Received invalid data. Expected numeric values for data_received and data_sent." >&2
        exit 1
    fi

    # Build JSON payload
    json_payload="{ \"data_received\": $data_received, \"data_sent\": $data_sent }"

    webhook_url="http://192.168.XXX.XXX:8123/api/webhook/uxg_wan_stats"

    # Send the data to Home Assistant
    curl "$webhook_url" \
         -H "Content-Type: application/json" \
         -d "@-" <<< "$json_payload"
else
    echo "Error: Unable to retrieve data for ppp0 interface." >&2
    exit 1
fi
```

### The crontab entry to run the script every 10 seconds
```
* * * * * ( /persistent/system/ppp0_stats.sh )
* * * * * ( sleep 10 ; /persistent/system/ppp0_stats.sh )
* * * * * ( sleep 20 ; /persistent/system/ppp0_stats.sh )
* * * * * ( sleep 30 ; /persistent/system/ppp0_stats.sh )
* * * * * ( sleep 40 ; /persistent/system/ppp0_stats.sh )
* * * * * ( sleep 50 ; /persistent/system/ppp0_stats.sh )
```
### Create 2 Input Number helpers
#### 1) WAN Bytes Received
#### 2) WAN Bytes Sent
```
Min Value: 0
Max Value: 9223372036854775807
Display mode: input field
Unit of measurement: Bytes
```

### Automation YAML to update the WAN Bytes Received and WAN Bytes Sent values
```yaml
alias: UXG WAN stats
description: UXG WAN stats
trigger:
  - platform: webhook
    allowed_methods:
      - POST
    local_only: true
    webhook_id: "uxg_wan_stats"
condition: []
action:
  - service: input_number.set_value
    metadata: {}
    data_template:
      value: "{{ trigger.json.data_received }}"
    target:
      entity_id: input_number.wan_bytes_received
  - service: input_number.set_value
    metadata: {}
    data_template:
      value: "{{ trigger.json.data_sent }}"
    target:
      entity_id: input_number.wan_bytes_sent
mode: single
```

### Create 2 statistics sensors to determine bytes/second using last 4 samples
```yaml
- platform: statistics
  name: "UXG WAN in Stats"
  entity_id: input_number.wan_bytes_received
  sampling_size: 3
  state_characteristic: change_second
  max_age:
    hours: 24

- platform: statistics
  name: "UXG WAN out Stats"
  entity_id: input_number.wan_bytes_sent
  sampling_size: 3
  state_characteristic: change_second
  max_age:
    hours: 24
```

### Download and Upload template sensors that converts bytes to Mbits
```yaml
template:
- sensor:
  - name: "Internet Download"
    state: "{{ states('sensor.uxg_wan_in_stats')|float *8 /1024 /1024 |round(2) }}"
    unit_of_measurement: "MBps"
    state_class: measurement

  - name: "Internet Upload"
    state: "{{ states('sensor.uxg_wan_out_stats')|float *8 /1024 /1024 |round(2) }}"
    unit_of_measurement: "MBps"
    state_class: measurement
```
