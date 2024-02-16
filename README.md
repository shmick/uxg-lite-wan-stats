# UXG Lite WAN Stats for Home Assistant

## Why is this needed?

The Ubiquiti UniFi UXG-Lite does not have SNMP enabled on it like it's predecessor, the USG, so we need an alternative way to monitor the WAN stats.

## How does this work?

By installing a script into the `/persistent/system` volume on the UXG-Lite and running the script every 10 seconds via a cron job. The script sends the WAN stats to Home Assistant via a [webhook trigger](https://www.home-assistant.io/docs/automation/trigger/#webhook-trigger)

## Will this work after a firmware update on the UXG-Lite?

The script that was saved on the filesystem should remain, but you will most likely need to add the crontab lines back

## How do I get this running?

### Step 1 - install the `send_wan_stats.sh` script on your UXG-Lite 

* [How to SSH into a UXG Pro - this should also work for a UXG-Lite](https://support.hostifi.com/en/articles/6224334-unifi-how-to-ssh-into-a-uxg-pro)

Be sure to make the script executable `chmod +x /persistent/system/send_wan_stats.sh`

```bash
#!/bin/bash

# Using ppp0 for the WAN interface. Use the correct interface for your connection.

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
    curl -m 5 "$webhook_url" \
         -H "Content-Type: application/json" \
         -d "@-" <<< "$json_payload"
else
    echo "Error: Unable to retrieve data for ppp0 interface." >&2
    exit 1
fi
```

### Step 2 - Add the following entries to the root crontab on your UXG-Lite

```bash
* * * * * ( /persistent/system/send_wan_stats.sh )
* * * * * ( sleep 10 ; /persistent/system/send_wan_stats.sh )
* * * * * ( sleep 20 ; /persistent/system/send_wan_stats.sh )
* * * * * ( sleep 30 ; /persistent/system/send_wan_stats.sh )
* * * * * ( sleep 40 ; /persistent/system/send_wan_stats.sh )
* * * * * ( sleep 50 ; /persistent/system/send_wan_stats.sh )
```

### Step 3 - Create [Input Number](https://www.home-assistant.io/integrations/input_number/) helpers in Home Assistant
1. WAN Bytes Received
2. WAN Bytes Sent

#### Settings for both:
> Min Value: 0  
Max Value: 9223372036854775807  
Display mode: input field  
Unit of measurement: Bytes

### Step 4 - Create an [Automation](https://www.home-assistant.io/getting-started/automation/) to update the Input Numbers

You should be able to use the YAML below without needing to edit anything
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

### Step 5 - Create [statistics sensors](https://www.home-assistant.io/integrations/statistics/) to determine bytes/sec change rate

This will be added to [configuration.yaml](https://www.home-assistant.io/docs/configuration/)
```yaml
sensor:
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

### Step 6 - Create [template](https://www.home-assistant.io/integrations/template) sensors that coverts bytes/sec into Mbits/sec  

This will be added to [configuration.yaml](https://www.home-assistant.io/docs/configuration/)

```yaml
template:
  - sensor:
      - name: "Internet Download"
        state: "{{ states('sensor.uxg_wan_in_stats')|float(default=0) *8 /1024 /1024 |round(2) }}"
        unit_of_measurement: "MBps"
        state_class: measurement
      - name: "Internet Upload"
        state: "{{ states('sensor.uxg_wan_out_stats')|float(default=0) *8 /1024 /1024 |round(2) }}"
        unit_of_measurement: "MBps"
        state_class: measurement
```

### Step 7 - Exclude the automation and input numbers from the recorder to cut down on logger noise

This will be added to [configuration.yaml](https://www.home-assistant.io/docs/configuration/) 

```yaml
recorder:
  exclude:
    entities:
      - automation.uxg_wan_stats
      - input_number.wan_bytes_received
      - input_number.wan_bytes_sent
```
