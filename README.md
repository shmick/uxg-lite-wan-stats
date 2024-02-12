## Since I'm using PPPoE with my ISP, I'm monitoring the ppp0 interface

### The script to gather stats and send them to Home Assistant

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

### Automation YAML to create 2 events from the incoming data
```yaml
alias: UXG ppp0 stats
description: UXG ppp0 stats
trigger:
  - platform: webhook
    allowed_methods:
      - POST
    local_only: true
    webhook_id: "uxg_wan_stats"
condition: []
action:
  - alias: Update Data Received
    event: set_ppp0_data_received
    event_data:
      state: "{{ trigger.json.data_received }}"
  - alias: Update Data Sent
    event: set_ppp0_data_sent
    event_data:
      state: "{{ trigger.json.data_sent }}"
mode: single
```

### Template sensors that update their values from the raw event data
```yaml
- trigger:
  - platform: event
    event_type: set_ppp0_data_received
  sensor:
  - name: UXG ppp0 Data Received
    unique_id: uxg_ppp0_data_received
    state: "{{ trigger.event.data.state }}"

- trigger:
  - platform: event
    event_type: set_ppp0_data_sent
  sensor:
  - name: UXG ppp0 Data Sent
    unique_id: uxg_ppp0_data_sent
    state: "{{ trigger.event.data.state }}"
```

### Statistics sensors to determine bytes/second using last 4 samples
```yaml
- platform: statistics
  name: "UXG WAN in Stats"
  entity_id: sensor.uxg_ppp0_data_received
  sampling_size: 4
  state_characteristic: change_second
  max_age:
    hours: 24

- platform: statistics
  name: "UXG WAN out Stats"
  entity_id: sensor.uxg_ppp0_data_sent
  sampling_size: 4
  state_characteristic: change_second
  max_age:
    hours: 24
```

### Download and Upload template sensors that converts bytes to Mbits
```
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
