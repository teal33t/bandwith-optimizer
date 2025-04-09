#!/usr/bin/env python
import os
import random
import datetime
from app import app, db
from app.models import (
    Device, Interface, Connection, SNMP, ICMP,
    TrafficClass, ClassMap, PolicyMap, PolicyEntry, 
    PolicyApplication, BandwidthStat, QoSMechanismType
)
from app.utils import encrypt_sensitive_data

def create_fake_data():
    """Create fake data for the bandwidth optimizer application"""
    print("Creating fake data for the bandwidth optimizer application...")
    
    # Clear existing data
    print("Clearing existing data...")
    db.session.query(PolicyApplication).delete()
    db.session.query(PolicyEntry).delete()
    db.session.query(PolicyMap).delete()
    db.session.query(ClassMap).delete()
    db.session.query(TrafficClass).delete()
    db.session.query(BandwidthStat).delete()
    db.session.query(Interface).delete()
    db.session.query(Device).delete()
    db.session.query(Connection).delete()
    db.session.query(SNMP).delete()
    db.session.query(ICMP).delete()
    db.session.commit()
    
    # Create fake devices
    print("Creating fake devices...")
    router_ips = [
        "192.168.1.1", "10.0.0.1", "172.16.0.1", 
        "192.168.2.1", "10.1.1.1", "172.17.0.1",
        "192.168.3.1", "10.2.2.1", "172.18.0.1"
    ]
    
    devices = []
    
    for i, ip in enumerate(router_ips):
        # Create connection
        connection = Connection(
            type=2,  # SSH
            status=1,  # Active
            username=f"admin{i+1}",
            password=encrypt_sensitive_data(f"password{i+1}")
        )
        db.session.add(connection)
        db.session.flush()
        
        # Create SNMP
        snmp = SNMP(
            status=1,  # Active
            version=2,  # SNMPv2
            comm_key=encrypt_sensitive_data(f"community{i+1}")
        )
        db.session.add(snmp)
        db.session.flush()
        
        # Create ICMP
        icmp = ICMP(
            status=1,  # Active
            avg_ping=random.randint(5, 50),
            interval_atmp=3
        )
        db.session.add(icmp)
        db.session.flush()
        
        # Create device
        device = Device(
            ip=ip,
            connection_id=connection.id,
            snmp_id=snmp.id,
            icmp_id=icmp.id
        )
        db.session.add(device)
        db.session.flush()
        devices.append(device)
    
    # Create interfaces for each device
    print("Creating interfaces for devices...")
    interfaces = []
    interface_types = ["GigabitEthernet", "FastEthernet", "Ethernet", "Serial"]
    
    for device in devices:
        # Create 3-5 interfaces per device
        for j in range(random.randint(3, 5)):
            interface_type = random.choice(interface_types)
            interface = Interface(
                device_id=device.id,
                ifname=f"{interface_type}{j}/0/{random.randint(0, 24)}"
            )
            db.session.add(interface)
            db.session.flush()
            interfaces.append(interface)
    
    # Create traffic classes
    print("Creating traffic classes...")
    traffic_classes = []
    class_names = ["Voice", "Video", "Management", "Bulk", "Best-Effort"]
    dscp_values = [46, 34, 16, 10, 0]
    
    for k, (name, dscp) in enumerate(zip(class_names, dscp_values)):
        traffic_class = TrafficClass(
            name=name,
            description=f"{name} traffic class",
            dscp_value=dscp
        )
        db.session.add(traffic_class)
        db.session.flush()
        traffic_classes.append(traffic_class)
    
    # Create class maps
    print("Creating class maps...")
    class_maps = []
    match_criteria = [
        ["ip dscp ef", "ip precedence 5"],
        ["ip dscp af41", "ip precedence 4"],
        ["ip dscp cs2", "ip precedence 2"],
        ["ip dscp af11", "ip precedence 1"],
        ["ip dscp default", "ip precedence 0"]
    ]
    
    for l, (traffic_class, criteria) in enumerate(zip(traffic_classes, match_criteria)):
        class_map = ClassMap(
            name=f"CLASS-{traffic_class.name.upper()}",
            description=f"Class map for {traffic_class.name} traffic",
            match_criteria=str(criteria),
            traffic_class_id=traffic_class.id
        )
        db.session.add(class_map)
        db.session.flush()
        class_maps.append(class_map)
    
    # Create policy maps
    print("Creating policy maps...")
    policy_maps = []
    policy_names = ["INGRESS-QOS", "EGRESS-QOS", "CORE-QOS"]
    
    for m, name in enumerate(policy_names):
        policy_map = PolicyMap(
            name=name,
            description=f"{name} policy map",
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow()
        )
        db.session.add(policy_map)
        db.session.flush()
        policy_maps.append(policy_map)
    
    # Create policy entries
    print("Creating policy entries...")
    for policy_map in policy_maps:
        for n, class_map in enumerate(class_maps):
            # Different QoS mechanisms based on traffic class
            if n == 0:  # Voice
                mechanism_type = QoSMechanismType.LLQ
                is_priority = True
                bandwidth_percent = 10
                bandwidth_kbps = None
                wred_min_threshold = None
                wred_max_threshold = None
                wred_max_probability = None
            elif n == 1:  # Video
                mechanism_type = QoSMechanismType.CBWFQ
                is_priority = False
                bandwidth_percent = 30
                bandwidth_kbps = None
                wred_min_threshold = None
                wred_max_threshold = None
                wred_max_probability = None
            elif n == 2:  # Management
                mechanism_type = QoSMechanismType.CBWFQ
                is_priority = False
                bandwidth_percent = 15
                bandwidth_kbps = None
                wred_min_threshold = None
                wred_max_threshold = None
                wred_max_probability = None
            elif n == 3:  # Bulk
                mechanism_type = QoSMechanismType.WRED
                is_priority = False
                bandwidth_percent = 25
                bandwidth_kbps = None
                wred_min_threshold = 20
                wred_max_threshold = 40
                wred_max_probability = 10
            else:  # Best-Effort
                mechanism_type = QoSMechanismType.WRED
                is_priority = False
                bandwidth_percent = 20
                bandwidth_kbps = None
                wred_min_threshold = 10
                wred_max_threshold = 30
                wred_max_probability = 10
            
            policy_entry = PolicyEntry(
                policy_map_id=policy_map.id,
                class_map_id=class_map.id,
                priority=n,
                bandwidth_percent=bandwidth_percent,
                bandwidth_kbps=bandwidth_kbps,
                is_priority=is_priority,
                mechanism_type=mechanism_type,
                wred_min_threshold=wred_min_threshold,
                wred_max_threshold=wred_max_threshold,
                wred_max_probability=wred_max_probability
            )
            db.session.add(policy_entry)
    
    # Apply policies to interfaces
    print("Applying policies to interfaces...")
    directions = ["inbound", "outbound"]
    
    for interface in interfaces[:len(interfaces)//2]:  # Apply to half of the interfaces
        policy_map = random.choice(policy_maps)
        direction = random.choice(directions)
        
        policy_application = PolicyApplication(
            interface_id=interface.id,
            policy_map_id=policy_map.id,
            direction=direction,
            is_active=True,
            applied_at=datetime.datetime.utcnow()
        )
        db.session.add(policy_application)
    
    # Create bandwidth statistics
    print("Creating bandwidth statistics...")
    now = datetime.datetime.utcnow()
    
    for interface in interfaces:
        # Create 24 hours of data points (one per hour)
        for hour in range(24):
            timestamp = now - datetime.timedelta(hours=24-hour)
            
            # Create a daily traffic pattern
            hour_of_day = (timestamp.hour + 3) % 24  # Shift by 3 hours for time zone
            
            # Business hours have higher traffic
            if 8 <= hour_of_day <= 18:
                base_traffic = random.uniform(0.5, 0.8)  # 50-80% utilization during business hours
            else:
                base_traffic = random.uniform(0.1, 0.3)  # 10-30% utilization during off hours
            
            # Add some randomness
            input_factor = base_traffic + random.uniform(-0.1, 0.1)
            output_factor = base_traffic + random.uniform(-0.1, 0.1)
            
            # Ensure factors are within bounds
            input_factor = max(0.05, min(0.95, input_factor))
            output_factor = max(0.05, min(0.95, output_factor))
            
            # Calculate rates based on interface type
            if "Gigabit" in interface.ifname:
                max_rate = 1000000  # 1 Gbps in Kbps
            elif "Fast" in interface.ifname:
                max_rate = 100000   # 100 Mbps in Kbps
            else:
                max_rate = 10000    # 10 Mbps in Kbps
            
            input_rate = int(max_rate * input_factor)
            output_rate = int(max_rate * output_factor)
            
            # Create bandwidth stat
            bandwidth_stat = BandwidthStat(
                interface_id=interface.id,
                timestamp=timestamp,
                input_rate_kbps=input_rate,
                output_rate_kbps=output_rate,
                input_packets=int(input_rate * 0.1 * random.uniform(0.9, 1.1)),
                output_packets=int(output_rate * 0.1 * random.uniform(0.9, 1.1)),
                input_errors=int(input_rate * 0.0001 * random.uniform(0, 2)),
                output_errors=int(output_rate * 0.0001 * random.uniform(0, 2))
            )
            db.session.add(bandwidth_stat)
    
    # Commit all changes
    db.session.commit()
    print("Fake data creation complete!")

if __name__ == "__main__":
    with app.app_context():
        create_fake_data()
