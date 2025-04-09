# QoS Bandwidth Optimizer

![Network QoS](https://img.shields.io/badge/Network-QoS-blue)
![Flask](https://img.shields.io/badge/Framework-Flask-green)
![Cisco](https://img.shields.io/badge/Supported-Cisco-orange)

<div align="center">
  <img src="logo.jpg" alt="QoS Bandwidth Optimizer Logo" width="300">
</div>

## Overview
A Flask application for managing Quality of Service (QoS) policies on network devices. Provides web-based interface for configuring and monitoring QoS settings.




### Cisco Routers and Switches
| Model Series | IOS Version | Notes |
|--------------|-------------|-------|
| Catalyst 2960-X/XS | 15.2+ | Full support |
| Catalyst 3750-X | 15.2+ | Full support |
| Catalyst 3850 | 15.2+ | Full support |
| Catalyst 9300 | 16.9+ | Basic functionality |

**Requirements:**
- SSHv2 access
- SNMP v2c/v3
- QoS capable IOS image


### Architecture
The QoS Bandwidth Optimizer follows a modular architecture:

1. **Web Interface Layer**: Flask-based frontend with Flask-AppBuilder for admin interfaces
2. **Business Logic Layer**: Core QoS policy management and device interaction logic
3. **Device Communication Layer**: SSH and SNMP-based communication with network devices
4. **Data Persistence Layer**: SQLAlchemy ORM with database models for all QoS components


---

## Features

- Centralized inventory of network devices
- Automated discovery of device interfaces via SNMP
- Connection status monitoring (SSH, SNMP, ICMP)
- Bulk operations for multi-device configuration
- Visual policy creation wizards
- Support for CBWFQ, LLQ, and WRED mechanisms
- Traffic classification based on multiple criteria
- Policy validation before deployment
- Automatic CLI command generation
- Real-time interface statistics collection
- Historical bandwidth usage graphs
- Predefined traffic classes for common applications
- Custom traffic class creation
- DSCP marking configuration

---

## Installation

### Prerequisites
- Python 3.8 or higher
- pip and virtualenv
- Network access to managed devices
- SNMP access to devices for monitoring
- SSH access to devices for configuration

```bash
# Clone the repository
git clone https://github.com/teal33t/bandwith-optimizer.git
cd bandwith-optimizer

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env file with your settings

# Initialize database
flask db upgrade
flask initdb

# Start application
flask run
```

### Development Setup
For development environments:

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run with debug mode
flask run --debug
```

---


## CLI Commands

| Command | Description | Options |
|---------|-------------|---------|
| `flask run` | Start development server | `--host`, `--port`, `--debug` |
| `flask initdb` | Initialize database | `--force` to recreate tables |
| `flask fake-add` | Add test data | `--count` for number of devices |
| `flask fake-remove` | Clear test data | `--all` to remove everything |
| `flask db upgrade` | Run database migrations | |
| `flask db downgrade` | Revert database migrations | |
| `flask translate` | Update translations | `--lang` for language |
| `flask routes` | List all application routes | |

### Custom Management Commands
```bash
# Collect bandwidth statistics for all devices
flask collect-stats

# Verify device connectivity
flask check-devices

# Export configuration report
flask export-config --format=pdf
```


---


## Configuration
Environment variables (set in `.env` file):

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Application secret key | `your-secret-key-here` |
| `SQLALCHEMY_DATABASE_URI` | Database connection | `sqlite:///app.db` |
| `APP_NAME` | Application name | `QoS Optimizer` |
| `APP_THEME` | UI theme | `dark` or `light` |
| `AUTH_TYPE` | Authentication method | `local` or `ldap` |
| `ENCRYPTION_KEY` | Key for credential encryption | `fernet-key-here` |
| `MRTG_CFG_BASE_PATH` | Path for MRTG configs | `/var/www/mrtg/` |
| `SUDO_PASSWORD` | For MRTG operations (dev only) | `password` |
| `LOG_LEVEL` | Application logging level | `INFO` |
| `DEVICE_TIMEOUT` | Device connection timeout | `30` |

### Database Schema
The application uses the following core models:

- **Device**: Network device information
- **Connection**: SSH/Telnet connection details
- **SNMP**: SNMP configuration for monitoring
- **ICMP**: Ping monitoring configuration
- **Interface**: Network interfaces on devices
- **TrafficClass**: Application traffic categories
- **ClassMap**: Traffic matching criteria
- **PolicyMap**: QoS policy definitions
- **PolicyEntry**: QoS mechanisms within policies
- **PolicyApplication**: Association of policies to interfaces
- **BandwidthStat**: Collected bandwidth statistics

---

## Usage

### Initial Setup
1. Access web interface at `http://localhost:3333`
2. Login with admin credentials (default: admin/admin)
3. Add network devices using device credentials
4. Verify device connectivity (SSH, SNMP, ICMP)
5. Discover device interfaces

### QoS Configuration Workflow
1. Create traffic classes for your applications
2. Define class maps with match criteria
3. Create policy maps with QoS mechanisms
4. Apply policies to device interfaces
5. Verify policy application

### Monitoring
1. View real-time bandwidth statistics
2. Analyze historical usage patterns
3. Check for QoS policy effectiveness
4. Export reports for capacity planning

### Troubleshooting
1. Verify device connectivity status
2. Check interface statistics for errors
3. Review policy application logs
4. Validate QoS configuration on devices

<div align="center">
  <img width="550"  src="images/mark-engine.png" alt="QoS Policy Configuration">
  <p><em>QoS policy configuration interface</em></p>
</div>

---


## Network Topology

```
                   +-------------+
                   | Bandwidth   |
                   | Optimizer   |
                   +------+------+
                          |
                          |
+--------+        +-------+-------+        +--------+
| Router |--------| Core Router   |--------| Router |
| Edge1  |        | (QoS Policies)|        | Edge2  |
+---+----+        +-------+-------+        +----+---+
    |                     |                     |
+---+----+         +-----+------+         +----+---+
| Host1  |         | Host2      |         | Host3  |
| (VoIP) |         | (Video)    |         | (Data) |
+--------+         +------------+         +--------+
```

![Traffic Classes](images/traffic-class.png)
*Traffic class configuration for QoS policies*

---

## Device Management

![Device List](images/device-list.png)
*Device management interface showing connected network devices*

![Interface List](images/interfaces-list.png)
*Network interfaces available for QoS configuration*

## QoS Engines


<div align="center">
  <img width="450" src="images/mark-engine.png" alt="Mark Engine Advanced Configuration">
  <img width="450" src="images/mark-engine1.png" alt="Mark Engine Advanced Configuration">
  <img width="450" src="images/mark-engine2.png" alt="Mark Engine Advanced Configuration">
  <img width="450" src="images/mark-engine3.png" alt="Mark Engine Advanced Configuration">
  <img width="450" src="images/mark-engine4.png" alt="Mark Engine Advanced Configuration">
  <p><em>Mark Engine advanced configuration options</em></p>
</div>
<div align="center">
  <img width="450" src="images/drop-engine.png" alt="Drop Engine Configuration">
  <p><em>Drop Engine configuration for packet handling</em></p>
</div>

![Dashboard Preview](images/bandwidth-list.png)
*Dashboard showing device bandwidth status and utilization*


## Appendix: QoS Terminology

### Quality of Service Mechanisms
- **CBWFQ**: Class-Based Weighted Fair Queuing
- **LLQ**: Low Latency Queuing
- **WRED**: Weighted Random Early Detection
- **DSCP**: Differentiated Services Code Point

### Network Concepts
- **Bandwidth**: Maximum data transfer rate
- **Latency**: Time delay between packets
- **Jitter**: Variation in packet delay
- **Packet Loss**: Percentage of lost packets

### Application Components
- **Traffic Class**: Logical grouping of traffic flows
- **Policy Map**: Collection of QoS policies
- **Class Map**: Traffic classification criteria
- **Marking**: Tagging packets with QoS info



---


## ⚠️ Cautions and Disclaimers

This application is optimized for small to medium-sized networks** (up to ~50 devices) and is ideal for branch offices, small campuses, or departmental networks.

### Legal Disclaimer
This software is provided "as is", without warranty of any kind, express or implied. The authors and contributors are not liable for any damages or network outages resulting from the use of this software. Users are responsible for testing and validating all configurations before deployment to production environments.

By using this application, you acknowledge that modifying network device configurations carries inherent risks, and you accept responsibility for changes made to your network infrastructure.
