# QoS Bandwidth Optimizer

![Network QoS](https://img.shields.io/badge/Network-QoS-blue)
![Flask](https://img.shields.io/badge/Framework-Flask-green)
![Cisco](https://img.shields.io/badge/Supported-Cisco-orange)

## Overview
A Flask application for managing Quality of Service (QoS) policies on network devices. Provides web-based interface for configuring and monitoring QoS settings.

---

## Features
- 📊 Device management dashboard
- ⚙️ QoS policy configuration
- 📈 Real-time bandwidth monitoring
- 🗂️ Traffic class management
- 🔐 User authentication

---

## Installation

```bash
# Clone the repository
git clone https://github.com/your-repo/qos-bandwidth-optimizer.git
cd qos-bandwidth-optimizer

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

---

## Supported Devices

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

---

## Usage
1. Access web interface at `http://localhost:3333`
2. Login with admin credentials
3. Add network devices using device credentials
4. Configure QoS policies through the web interface
5. Monitor bandwidth usage in real-time

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `flask run` | Start development server |
| `flask initdb` | Initialize database |
| `flask fake-add` | Add test data |
| `flask fake-remove` | Clear test data |

---

## Network Topology

```mermaid
graph TD
    A[Management Workstation\n(QoS Bandwidth Optimizer)] --> B[Core Router\n(QoS Policies)]
    B --> C[Router Edge1]
    B --> D[Router Edge2]
    C --> E[Host1\n(VoIP Traffic)]
    D --> F[Host3\n(Data Traffic)]
    B --> G[Host2\n(Video Traffic)]
```

---

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
