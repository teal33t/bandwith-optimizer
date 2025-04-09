# QoS Bandwidth Optimizer

## Overview
A Flask application for managing Quality of Service (QoS) policies on network devices. Provides web-based interface for configuring and monitoring QoS settings.

## Supported Devices
- Cisco routers and switches (IOS/IOS-XE)
  - Tested with Catalyst 2960, 3750, 3850 series
  - Requires IOS 15.x or later
- Devices must support:
  - SSH access for configuration
  - SNMP for monitoring
  - Standard QoS mechanisms (CBWFQ, LLQ, WRED)

## Features
- Device management dashboard
- QoS policy configuration
- Real-time bandwidth monitoring
- Traffic class management
- User authentication

## Installation
1. Clone the repository
2. Create virtual environment: `python -m venv venv`
3. Activate venv: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env`: `cp .env.example .env`
6. Edit the `.env` file with your configuration settings
7. Run migrations: `flask db upgrade`
8. Initialize database: `flask initdb`
9. Start server: `flask run`

## Configuration
The application uses environment variables loaded from a `.env` file for configuration. Edit the `.env` file to set:
- `SECRET_KEY` - App secret key (generate a secure random key for production)
- `SQLALCHEMY_DATABASE_URI` - Database connection string
- `APP_NAME` - Application name
- `APP_THEME` - UI theme
- `AUTH_TYPE` - Authentication type

## Usage
1. Access web interface at http://localhost:3333
2. Login with admin credentials
3. Add network devices
4. Configure QoS policies

## CLI Commands
The application provides several Flask CLI commands:

- `flask run` - Start the application server
- `flask initdb` - Initialize the database
- `flask fake-add` - Add fake data to the database for testing
- `flask fake-remove` - Remove all data from the database


# QoS Terminology Glossary

## Quality of Service Mechanisms
- **CBWFQ (Class-Based Weighted Fair Queuing)**: Allocates bandwidth to traffic classes based on weights
- **LLQ (Low Latency Queuing)**: Strict priority queuing for latency-sensitive traffic
- **WRED (Weighted Random Early Detection**)**: Congestion avoidance technique that drops packets probabilistically
- **DSCP (Differentiated Services Code Point)**: 6-bit field in IP header for classifying network traffic

## Network Concepts
- **Bandwidth**: Maximum data transfer rate of a network path
- **Latency**: Time delay between sending and receiving packets
- **Jitter**: Variation in packet delay times
- **Packet Loss**: Percentage of packets that fail to reach destination

## Application Components
- **Traffic Class**: Logical grouping of similar traffic flows
- **Policy Map**: Collection of QoS policies applied to interfaces
- **Class Map**: Defines matching criteria for traffic classification
- **Marking**: Process of tagging packets with QoS information

## Device Support
- **Cisco IOS**: Tested with versions 15.2+
- **Catalyst Switches**: Supported models:
  - 2960-X/XS
  - 3750-X/XS
  - 3850 SMI/EMI
  - 9300 (basic functionality)
- **Minimum Requirements**:
  - SSHv2 access
  - SNMP v2c/v3
  - QoS capable IOS image


## Topology
                   +-------------+
                   | Management  |
                   | Workstation |
                   | (Your App)  |
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