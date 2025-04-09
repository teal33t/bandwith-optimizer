import shlex
import subprocess
import socket
import struct
import os
import json
import time
import re
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload
from sqlalchemy import desc
from . import db
from .models import (
    Device, Interface, Connection, SNMP, ICMP,
    TrafficClass, ClassMap, PolicyMap, PolicyEntry, 
    PolicyApplication, BandwidthStat, QoSMechanismType
)
from cryptography.fernet import Fernet

# Configuration constants
SUDO_PASSWORD = os.environ.get('SUDO_PASSWORD', '123')  # Should be stored securely in production
CFGMAKER_EXEC_PATH = 'cfgmaker'
MRTG_CFG_BASE_PATH = '/var/www/mrtg/'
# Generate a valid Fernet key
from cryptography.fernet import Fernet
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', Fernet.generate_key().decode())  # Should be stored securely
cipher_suite = Fernet(ENCRYPTION_KEY.encode())

# Encryption/decryption functions
def encrypt_sensitive_data(data):
    """Encrypt sensitive data like passwords and SNMP community strings"""
    if not data:
        return data
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_sensitive_data(encrypted_data):
    """Decrypt sensitive data"""
    if not encrypted_data:
        return encrypted_data
    return cipher_suite.decrypt(encrypted_data.encode()).decode()

def add_new_device(router_ip, connections_type, ssh_username, ssh_password, ssh_status, 
                 snmp_version, snmp_community, snmp_status, interval, ping_status, interfaces_list):
    """Add a new device and its associated data to the database"""
    try:
        # Check if device already exists
        existing_device = db.session.query(Device).filter_by(ip=router_ip).first()
        if existing_device:
            # Update existing device instead of creating new one
            connection = existing_device.connection
            snmp = existing_device.snmp
            icmp = existing_device.icmp
            
            # Update connection data
            connection.type = connections_type
            connection.status = ssh_status
            connection.username = ssh_username
            connection.password = encrypt_sensitive_data(ssh_password)
            
            # Update SNMP data
            snmp.status = snmp_status
            snmp.version = snmp_version
            snmp.comm_key = encrypt_sensitive_data(snmp_community)
            
            # Update ICMP data
            icmp.status = ping_status
            icmp.interval_atmp = interval
            
            device_id = existing_device.id
            
        else:
            # Create new connection
            connection = Connection(
                type=connections_type,
                status=ssh_status,
                username=ssh_username,
                password=encrypt_sensitive_data(ssh_password)
            )
            db.session.add(connection)
            db.session.flush()
            
            # Create SNMP
            snmp = SNMP(
                status=snmp_status,
                version=snmp_version,
                comm_key=encrypt_sensitive_data(snmp_community)
            )
            db.session.add(snmp)
            db.session.flush()
            
            # Create ICMP
            icmp = ICMP(
                status=ping_status,
                avg_ping=0,
                interval_atmp=interval
            )
            db.session.add(icmp)
            db.session.flush()
            
            # Create device
            device = Device(
                ip=router_ip,
                connection_id=connection.id,
                snmp_id=snmp.id,
                icmp_id=icmp.id
            )
            db.session.add(device)
            db.session.flush()
            device_id = device.id
            
        # Delete existing interfaces if any
        db.session.query(Interface).filter_by(device_id=device_id).delete()
        
        # Create new interfaces
        for interface in interfaces_list:
            db.session.add(Interface(
                device_id=device_id,
                ifname=interface
            ))
        
        db.session.commit()
        return device_id
    
    except Exception as e:
        db.session.rollback()
        raise

def update_interfaces(router_ip, snmp_community):
    """Update interface information for a device using SNMP"""
    if not router_ip or not snmp_community:
        return []
        
    interfaces_list = []   
    now = datetime.now()
    date_str = now.strftime("%Y_%m_%d_%H_%M_%S_%f")
    ip_str = str(router_ip).replace(".", "_")
    
    # Create config path 
    path = os.path.join(MRTG_CFG_BASE_PATH, f"{date_str}_{ip_str}_mrtg.cfg")
    cmd_cfgmaker = f"{CFGMAKER_EXEC_PATH} {snmp_community}@{router_ip} > {path}"
    
    try:
        # Execute cfgmaker command with sudo
        p = os.system(f'echo {SUDO_PASSWORD}|sudo -S {cmd_cfgmaker}')
        
        # Read interfaces from config file
        if os.path.exists(path):
            with open(path, "r") as cfg_file:
                for line in cfg_file:
                    if "Interface" in line:
                        try:
                            start_idx = line.index(">> Descr: '") + len(">> Descr: '")
                            end_idx = line.index("' | Name")
                            interfaces = line[start_idx:end_idx]
                            interfaces_list.append(interfaces)
                        except (ValueError, IndexError):
                            continue
                            
            # Clean up temporary config file
            os.system(f'echo {SUDO_PASSWORD}|sudo -S rm {path}')
    
    except Exception as e:
        raise
        
    # Update database with interfaces
    device_id = get_id_by_device_ip(router_ip)
    if device_id:
        try:
            # Delete existing interfaces
            db.session.query(Interface).filter_by(device_id=device_id).delete()
            
            # Add new interfaces
            for interface in interfaces_list:
                db.session.add(Interface(
                    device_id=device_id,
                    ifname=interface
                ))
            
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise
    
    return interfaces_list

def ping_ip(ip, interval):
    """Ping an IP address and return status and output"""
    command = f"ping -c {interval} {ip.strip()}"
    cmd = shlex.split(command)
    
    try:
        output = subprocess.check_output(cmd, universal_newlines=True)
        return 1, output
    except subprocess.CalledProcessError as e:
        return 0, str(e)
    except Exception as e:
        return 0, str(e)

def get_id_by_device_ip(ip):
    """Get device ID by IP address"""
    device = db.session.query(Device).filter_by(ip=ip).first()
    return device.id if device else 0

def get_ip_by_device_id(device_id):
    """Get device IP by ID"""
    device = db.session.query(Device).get(device_id)
    return device.ip if device else ""

def get_device_interfaces(device_id):
    """Get interfaces for a device"""
    device = db.session.query(Device).get(device_id)
    if not device:
        return []
    return [(i.id, i.device_id, i.ifname) for i in device.interfaces]

def get_all_devices():
    """Get all devices with their status information"""
    devices = db.session.query(Device).options(
        joinedload(Device.snmp),
        joinedload(Device.icmp),
        joinedload(Device.connection)
    ).all()
    
    devices_info = []
    html_remake = []
    
    for device in devices:
        snmp_status = device.snmp.status if device.snmp else 0
        ping_status = device.icmp.status if device.icmp else 0
        ssh_status = device.connection.status if device.connection else 0
        
        devices_info.append([
            device.id,
            device.ip,
            int(snmp_status),
            int(ping_status),
            int(ssh_status)
        ])
        
        # Format status values for HTML display
        html_remake.append([
            device.id,
            device.ip,
            'green' if int(snmp_status) == 1 else 'red',
            'green' if int(ping_status) == 1 else 'red',
            'green' if int(ssh_status) == 1 else 'red'
        ])
    
    return devices_info, html_remake

# QoS Management Functions

def create_traffic_class(name, description=None, dscp_value=None):
    """Create a new traffic class for QoS classification"""
    try:
        # Check if traffic class already exists
        existing_class = db.session.query(TrafficClass).filter_by(name=name).first()
        if existing_class:
            return existing_class.id
            
        # Create new traffic class
        traffic_class = TrafficClass(
            name=name,
            description=description,
            dscp_value=dscp_value
        )
        db.session.add(traffic_class)
        db.session.commit()
        return traffic_class.id
    except Exception as e:
        db.session.rollback()
        raise

def create_class_map(name, match_criteria, traffic_class_id, description=None):
    """Create a new class map with match criteria"""
    try:
        # Create new class map
        class_map = ClassMap(
            name=name,
            description=description,
            match_criteria=json.dumps(match_criteria),
            traffic_class_id=traffic_class_id
        )
        db.session.add(class_map)
        db.session.commit()
        return class_map.id
    except Exception as e:
        db.session.rollback()
        raise

def create_policy_map(name, description=None):
    """Create a new policy map"""
    try:
        # Check if policy map already exists
        existing_policy = db.session.query(PolicyMap).filter_by(name=name).first()
        if existing_policy:
            return existing_policy.id
            
        # Create new policy map
        policy_map = PolicyMap(
            name=name,
            description=description,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(policy_map)
        db.session.commit()
        return policy_map.id
    except Exception as e:
        db.session.rollback()
        raise

def add_policy_entry(policy_map_id, class_map_id, mechanism_type, priority=0, 
                    bandwidth_percent=None, bandwidth_kbps=None, is_priority=False,
                    wred_min_threshold=None, wred_max_threshold=None, wred_max_probability=None):
    """Add an entry to a policy map"""
    try:
        # Create policy entry
        entry = PolicyEntry(
            policy_map_id=policy_map_id,
            class_map_id=class_map_id,
            priority=priority,
            bandwidth_percent=bandwidth_percent,
            bandwidth_kbps=bandwidth_kbps,
            is_priority=is_priority,
            mechanism_type=mechanism_type,
            wred_min_threshold=wred_min_threshold,
            wred_max_threshold=wred_max_threshold,
            wred_max_probability=wred_max_probability
        )
        db.session.add(entry)
        db.session.commit()
        return entry.id
    except Exception as e:
        db.session.rollback()
        raise

def apply_policy_to_interface(interface_id, policy_map_id, direction):
    """Apply a policy map to an interface"""
    try:
        # Check if policy is already applied
        existing_application = db.session.query(PolicyApplication).filter_by(
            interface_id=interface_id,
            policy_map_id=policy_map_id,
            direction=direction
        ).first()
        
        if existing_application:
            existing_application.is_active = True
            existing_application.applied_at = datetime.utcnow()
            db.session.commit()
            return existing_application.id
            
        # Create new policy application
        application = PolicyApplication(
            interface_id=interface_id,
            policy_map_id=policy_map_id,
            direction=direction,
            is_active=True,
            applied_at=datetime.utcnow()
        )
        db.session.add(application)
        db.session.commit()
        
        # Generate and apply configuration to device
        interface = db.session.query(Interface).get(interface_id)
        if interface:
            device = db.session.query(Device).get(interface.device_id)
            if device:
                apply_qos_config_to_device(device.id, interface.id, policy_map_id, direction)
        
        return application.id
    except Exception as e:
        db.session.rollback()
        raise

def remove_policy_from_interface(interface_id, policy_map_id, direction):
    """Remove a policy map from an interface"""
    try:
        application = db.session.query(PolicyApplication).filter_by(
            interface_id=interface_id,
            policy_map_id=policy_map_id,
            direction=direction,
            is_active=True
        ).first()
        
        if application:
            application.is_active = False
            db.session.commit()
            
            # Remove configuration from device
            interface = db.session.query(Interface).get(interface_id)
            if interface:
                device = db.session.query(Device).get(interface.device_id)
                if device:
                    remove_qos_config_from_device(device.id, interface.id, policy_map_id, direction)
            
            return True
        return False
    except Exception as e:
        db.session.rollback()
        raise

def get_interface_policies(interface_id):
    """Get all active policies applied to an interface"""
    try:
        policies = db.session.query(PolicyApplication).filter_by(
            interface_id=interface_id,
            is_active=True
        ).all()
        
        result = []
        for policy in policies:
            policy_map = db.session.query(PolicyMap).get(policy.policy_map_id)
            if policy_map:
                result.append({
                    'id': policy.id,
                    'policy_map_id': policy.policy_map_id,
                    'policy_name': policy_map.name,
                    'direction': policy.direction,
                    'applied_at': policy.applied_at
                })
        
        return result
    except Exception as e:
        raise

# Bandwidth Monitoring Functions

def collect_interface_bandwidth_stats(device_id):
    """Collect bandwidth statistics for all interfaces on a device"""
    try:
        device = db.session.query(Device).get(device_id)
        if not device or not device.snmp or device.snmp.status != 1:
            return False
            
        snmp_community = decrypt_sensitive_data(device.snmp.comm_key)
        
        for interface in device.interfaces:
            # Use SNMP to get interface statistics
            stats = get_interface_stats_via_snmp(device.ip, snmp_community, interface.ifname)
            if stats:
                # Create new bandwidth stat record
                bandwidth_stat = BandwidthStat(
                    interface_id=interface.id,
                    timestamp=datetime.utcnow(),
                    input_rate_kbps=stats.get('input_rate_kbps', 0),
                    output_rate_kbps=stats.get('output_rate_kbps', 0),
                    input_packets=stats.get('input_packets', 0),
                    output_packets=stats.get('output_packets', 0),
                    input_errors=stats.get('input_errors', 0),
                    output_errors=stats.get('output_errors', 0)
                )
                db.session.add(bandwidth_stat)
        
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        raise

def get_interface_stats_via_snmp(ip, community, interface_name):
    """Get interface statistics using SNMP"""
    # This would normally use a library like pysnmp to query the device
    # For demonstration, we'll return simulated data
    return {
        'input_rate_kbps': float(random.randint(1000, 10000)),
        'output_rate_kbps': float(random.randint(1000, 10000)),
        'input_packets': random.randint(10000, 100000),
        'output_packets': random.randint(10000, 100000),
        'input_errors': random.randint(0, 10),
        'output_errors': random.randint(0, 10)
    }

def get_interface_bandwidth_history(interface_id, hours=24):
    """Get bandwidth history for an interface"""
    try:
        since = datetime.utcnow() - timedelta(hours=hours)
        stats = db.session.query(BandwidthStat).filter(
            BandwidthStat.interface_id == interface_id,
            BandwidthStat.timestamp >= since
        ).order_by(BandwidthStat.timestamp).all()
        
        result = []
        for stat in stats:
            result.append({
                'timestamp': stat.timestamp.isoformat(),
                'input_rate_kbps': stat.input_rate_kbps,
                'output_rate_kbps': stat.output_rate_kbps,
                'input_packets': stat.input_packets,
                'output_packets': stat.output_packets,
                'input_errors': stat.input_errors,
                'output_errors': stat.output_errors
            })
        
        return result
    except Exception as e:
        raise

# Device Configuration Functions

def apply_qos_config_to_device(device_id, interface_id, policy_map_id, direction):
    """Generate and apply QoS configuration to a device"""
    try:
        device = db.session.query(Device).get(device_id)
        if not device or not device.connection or device.connection.status != 1:
            return False
            
        interface = db.session.query(Interface).get(interface_id)
        if not interface:
            return False
            
        policy_map = db.session.query(PolicyMap).get(policy_map_id)
        if not policy_map:
            return False
            
        # Generate configuration commands
        config_commands = generate_qos_config(policy_map, interface, direction)
        
        # Apply configuration to device
        ssh_username = device.connection.username
        ssh_password = decrypt_sensitive_data(device.connection.password)
        
        # This would normally use a library like paramiko or netmiko to connect to the device
        # For demonstration, we'll just print the commands
        print(f"Applying QoS configuration to {device.ip}:")
        for cmd in config_commands:
            print(f"  {cmd}")
            
        return True
    except Exception as e:
        raise

def remove_qos_config_from_device(device_id, interface_id, policy_map_id, direction):
    """Remove QoS configuration from a device"""
    try:
        device = db.session.query(Device).get(device_id)
        if not device or not device.connection or device.connection.status != 1:
            return False
            
        interface = db.session.query(Interface).get(interface_id)
        if not interface:
            return False
            
        policy_map = db.session.query(PolicyMap).get(policy_map_id)
        if not policy_map:
            return False
            
        # Generate removal commands
        removal_commands = generate_qos_removal_config(policy_map, interface, direction)
        
        # Apply configuration to device
        ssh_username = device.connection.username
        ssh_password = decrypt_sensitive_data(device.connection.password)
        
        # This would normally use a library like paramiko or netmiko to connect to the device
        # For demonstration, we'll just print the commands
        print(f"Removing QoS configuration from {device.ip}:")
        for cmd in removal_commands:
            print(f"  {cmd}")
            
        return True
    except Exception as e:
        raise

def generate_qos_config(policy_map, interface, direction):
    """Generate Cisco IOS QoS configuration commands"""
    commands = []
    
    # Add class-map configurations
    for entry in policy_map.entries:
        class_map = entry.class_map
        traffic_class = class_map.traffic_class
        
        # Parse match criteria from JSON
        match_criteria = json.loads(class_map.match_criteria)
        
        # Add class-map configuration
        commands.append(f"class-map {class_map.name}")
        for match in match_criteria:
            commands.append(f" match {match}")
        
        # Add DSCP marking if specified
        if traffic_class.dscp_value is not None:
            commands.append(f" set ip dscp {traffic_class.dscp_value}")
    
    # Add policy-map configuration
    commands.append(f"policy-map {policy_map.name}")
    
    for entry in policy_map.entries:
        commands.append(f" class {entry.class_map.name}")
        
        # Add QoS mechanism configuration based on type
        if entry.mechanism_type == QoSMechanismType.CBWFQ:
            if entry.bandwidth_percent:
                commands.append(f"  bandwidth percent {entry.bandwidth_percent}")
            elif entry.bandwidth_kbps:
                commands.append(f"  bandwidth {entry.bandwidth_kbps}")
                
        elif entry.mechanism_type == QoSMechanismType.LLQ:
            if entry.is_priority:
                if entry.bandwidth_kbps:
                    commands.append(f"  priority {entry.bandwidth_kbps}")
                else:
                    commands.append("  priority")
                    
        elif entry.mechanism_type == QoSMechanismType.WRED:
            commands.append("  random-detect")
            if entry.wred_min_threshold and entry.wred_max_threshold:
                commands.append(f"  random-detect precedence 0 {entry.wred_min_threshold} {entry.wred_max_threshold} {entry.wred_max_probability}")
    
    # Apply policy to interface
    commands.append(f"interface {interface.ifname}")
    if direction.lower() == 'inbound':
        commands.append(f" service-policy input {policy_map.name}")
    else:
        commands.append(f" service-policy output {policy_map.name}")
    
    return commands

def generate_qos_removal_config(policy_map, interface, direction):
    """Generate commands to remove QoS configuration"""
    commands = []
    
    # Remove policy from interface
    commands.append(f"interface {interface.ifname}")
    if direction.lower() == 'inbound':
        commands.append(f" no service-policy input {policy_map.name}")
    else:
        commands.append(f" no service-policy output {policy_map.name}")
    
    return commands

# Import for random data generation in the demo
import random
