from flask_appbuilder import Model
from sqlalchemy import Column, Integer, String, ForeignKey, Float, Boolean, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from flask_appbuilder.models.mixins import AuditMixin
import enum
from datetime import datetime

class Connection(Model):
    __tablename__ = 'connections_tbl'
    id = Column(Integer, primary_key=True)
    type = Column(Integer)
    status = Column(Integer)
    username = Column(String(100))
    password = Column(String(100))  # Should be encrypted in production
    devices = relationship('Device', back_populates='connection', lazy='dynamic')
    
    def __repr__(self):
        conn_type = "SSH" if self.type == 2 else "Telnet" if self.type == 1 else f"Unknown({self.type})"
        status = "Active" if self.status == 1 else "Inactive"
        return f"{conn_type} Connection ({status})"

class SNMP(Model):
    __tablename__ = 'snmp_tbl'
    id = Column(Integer, primary_key=True)
    status = Column(Integer)
    version = Column(Integer)
    comm_key = Column(String(100))  # Should be encrypted in production
    devices = relationship('Device', back_populates='snmp', lazy='dynamic')
    
    def __repr__(self):
        version = f"v{self.version}" if self.version in [1, 2, 3] else f"Unknown({self.version})"
        status = "Active" if self.status == 1 else "Inactive"
        return f"SNMP {version} ({status})"

class ICMP(Model):
    __tablename__ = 'icmps_tbl'
    id = Column(Integer, primary_key=True)
    status = Column(Integer)
    avg_ping = Column(Integer)
    interval_atmp = Column(Integer)
    devices = relationship('Device', back_populates='icmp', lazy='dynamic')
    
    def __repr__(self):
        status = "Active" if self.status == 1 else "Inactive"
        return f"ICMP ({status}, Avg: {self.avg_ping}ms)"

class Device(Model):
    __tablename__ = 'devices_tbl'
    id = Column(Integer, primary_key=True)
    ip = Column(String(15), unique=True)
    connection_id = Column(Integer, ForeignKey('connections_tbl.id'))
    snmp_id = Column(Integer, ForeignKey('snmp_tbl.id'))
    icmp_id = Column(Integer, ForeignKey('icmps_tbl.id'))
    interfaces = relationship('Interface', backref='device', lazy='dynamic', 
                            cascade='all, delete-orphan')
    
    connection = relationship('Connection', foreign_keys=[connection_id], back_populates='devices')
    snmp = relationship('SNMP', foreign_keys=[snmp_id], back_populates='devices')
    icmp = relationship('ICMP', foreign_keys=[icmp_id], back_populates='devices')
    
    def __repr__(self):
        return f"Device {self.ip}"

class Interface(Model):
    __tablename__ = 'interfaces_tbl'
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices_tbl.id'))
    ifname = Column(String(100))
    description = Column(String(255), nullable=True)
    bandwidth = Column(Integer, nullable=True)  # in Kbps
    is_active = Column(Boolean, default=True)
    policies = relationship('PolicyApplication', back_populates='interface', lazy='dynamic')
    bandwidth_stats = relationship('BandwidthStat', back_populates='interface', lazy='dynamic')
    
    def __repr__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"Interface {self.ifname} ({status})"

# QoS Models
class TrafficClass(Model):
    """Traffic classes for QoS classification"""
    __tablename__ = 'traffic_classes_tbl'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    description = Column(String(255), nullable=True)
    dscp_value = Column(Integer, nullable=True)  # DSCP value for marking
    class_maps = relationship('ClassMap', back_populates='traffic_class', lazy='dynamic')
    
    def __repr__(self):
        dscp_info = f" (DSCP: {self.dscp_value})" if self.dscp_value is not None else ""
        return f"Traffic Class: {self.name}{dscp_info}"

class ClassMap(Model):
    """Class maps for traffic matching criteria"""
    __tablename__ = 'class_maps_tbl'
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    description = Column(String(255), nullable=True)
    match_criteria = Column(Text)  # JSON string of match criteria
    traffic_class_id = Column(Integer, ForeignKey('traffic_classes_tbl.id'))
    traffic_class = relationship('TrafficClass', back_populates='class_maps')
    policy_entries = relationship('PolicyEntry', back_populates='class_map', lazy='dynamic')
    
    def __repr__(self):
        return f"Class Map: {self.name}"

class QoSMechanismType(enum.Enum):
    """Types of QoS mechanisms"""
    CBWFQ = 'CBWFQ'
    LLQ = 'LLQ'
    WRED = 'WRED'
    SHAPING = 'SHAPING'
    POLICING = 'POLICING'

class PolicyMap(Model):
    """Policy maps for QoS configuration"""
    __tablename__ = 'policy_maps_tbl'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    entries = relationship('PolicyEntry', back_populates='policy_map', lazy='dynamic')
    applications = relationship('PolicyApplication', back_populates='policy_map', lazy='dynamic')
    
    def __repr__(self):
        return f"Policy Map: {self.name}"

class PolicyEntry(Model):
    """Entries in a policy map"""
    __tablename__ = 'policy_entries_tbl'
    id = Column(Integer, primary_key=True)
    policy_map_id = Column(Integer, ForeignKey('policy_maps_tbl.id'))
    class_map_id = Column(Integer, ForeignKey('class_maps_tbl.id'))
    priority = Column(Integer, default=0)  # Higher number = higher priority
    bandwidth_percent = Column(Float, nullable=True)  # For CBWFQ
    bandwidth_kbps = Column(Integer, nullable=True)  # For CBWFQ
    is_priority = Column(Boolean, default=False)  # For LLQ
    mechanism_type = Column(Enum(QoSMechanismType), nullable=False)
    wred_min_threshold = Column(Integer, nullable=True)  # For WRED
    wred_max_threshold = Column(Integer, nullable=True)  # For WRED
    wred_max_probability = Column(Float, nullable=True)  # For WRED
    policy_map = relationship('PolicyMap', back_populates='entries')
    class_map = relationship('ClassMap', back_populates='policy_entries')
    
    def __repr__(self):
        class_name = self.class_map.name if self.class_map else "Unknown"
        return f"Policy Entry: {self.mechanism_type.value} for {class_name}"

class PolicyApplication(Model):
    """Application of policy maps to interfaces"""
    __tablename__ = 'policy_applications_tbl'
    id = Column(Integer, primary_key=True)
    interface_id = Column(Integer, ForeignKey('interfaces_tbl.id'))
    policy_map_id = Column(Integer, ForeignKey('policy_maps_tbl.id'))
    direction = Column(String(10))  # 'inbound' or 'outbound'
    is_active = Column(Boolean, default=True)
    applied_at = Column(DateTime, default=datetime.utcnow)
    interface = relationship('Interface', back_populates='policies')
    policy_map = relationship('PolicyMap', back_populates='applications')
    
    def __repr__(self):
        status = "Active" if self.is_active else "Inactive"
        policy_name = self.policy_map.name if self.policy_map else "Unknown"
        interface_name = self.interface.ifname if self.interface else "Unknown"
        return f"Policy Application: {policy_name} on {interface_name} ({self.direction}, {status})"

class BandwidthStat(Model):
    """Bandwidth statistics for interfaces"""
    __tablename__ = 'bandwidth_stats_tbl'
    id = Column(Integer, primary_key=True)
    interface_id = Column(Integer, ForeignKey('interfaces_tbl.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    input_rate_kbps = Column(Float)
    output_rate_kbps = Column(Float)
    input_packets = Column(Integer)
    output_packets = Column(Integer)
    input_errors = Column(Integer, default=0)
    output_errors = Column(Integer, default=0)
    interface = relationship('Interface', back_populates='bandwidth_stats')
    
    def __repr__(self):
        interface_name = self.interface.ifname if self.interface else "Unknown"
        time_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else "Unknown"
        return f"Bandwidth Stats for {interface_name} at {time_str} (In: {self.input_rate_kbps} kbps, Out: {self.output_rate_kbps} kbps)"
