from flask import render_template, flash, redirect, request, url_for, jsonify
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder import ModelView, BaseView, expose, has_access
from .models import (
    Connection, SNMP, ICMP, Device, Interface,
    TrafficClass, ClassMap, PolicyMap, PolicyEntry, 
    PolicyApplication, BandwidthStat, QoSMechanismType
)
from . import appbuilder, db
from .utils import (
    add_new_device, update_interfaces, ping_ip,
    get_device_interfaces, get_all_devices, get_ip_by_device_id,
    create_traffic_class, create_class_map, create_policy_map,
    add_policy_entry, apply_policy_to_interface, remove_policy_from_interface,
    get_interface_policies, collect_interface_bandwidth_stats,
    get_interface_bandwidth_history
)
import json
from datetime import datetime, timedelta

class MarkEngineView(BaseView):
    route_base = "/markengine"
    default_view = "rules"

    @expose("/rules")
    @has_access
    def rules(self):
        # Format traffic classes
        traffic_classes_data = []
        for tc in db.session.query(TrafficClass).all():
            traffic_classes_data.append({
                'id': tc.id,
                'name': tc.name,
                'description': tc.description,
                'dscp_value': tc.dscp_value
            })
        
        # Format class maps
        class_maps_data = []
        for cm in db.session.query(ClassMap).all():
            traffic_class_name = cm.traffic_class.name if cm.traffic_class else "Unknown"
            class_maps_data.append({
                'id': cm.id,
                'name': cm.name,
                'description': cm.description,
                'traffic_class_name': traffic_class_name,
                'match_criteria': cm.match_criteria
            })
        
        # Format policy maps
        policy_maps_data = []
        for pm in db.session.query(PolicyMap).all():
            policy_maps_data.append({
                'id': pm.id,
                'name': pm.name,
                'description': pm.description,
                'created_at': pm.created_at,
                'updated_at': pm.updated_at
            })
        
        return self.render_template(
            "mark_engine_rules.html",
            traffic_classes=traffic_classes_data,
            class_maps=class_maps_data,
            policy_maps=policy_maps_data
        )

    @expose("/wizard", methods=["GET", "POST"])
    @has_access
    def wizard(self):
        if request.method == "POST":
            # Create traffic class
            traffic_class_name = request.form.get('traffic_class_name')
            traffic_class_desc = request.form.get('traffic_class_desc')
            dscp_value = request.form.get('dscp_value')
            
            if dscp_value and dscp_value.isdigit():
                dscp_value = int(dscp_value)
            else:
                dscp_value = None
                
            traffic_class_id = create_traffic_class(
                name=traffic_class_name,
                description=traffic_class_desc,
                dscp_value=dscp_value
            )
            
            # Create class map
            class_map_name = request.form.get('class_map_name')
            class_map_desc = request.form.get('class_map_desc')
            match_criteria = request.form.getlist('match_criteria')
            
            class_map_id = create_class_map(
                name=class_map_name,
                description=class_map_desc,
                match_criteria=match_criteria,
                traffic_class_id=traffic_class_id
            )
            
            # Create policy map
            policy_map_name = request.form.get('policy_map_name')
            policy_map_desc = request.form.get('policy_map_desc')
            
            policy_map_id = create_policy_map(
                name=policy_map_name,
                description=policy_map_desc
            )
            
            # Add policy entry
            mechanism_type_str = request.form.get('mechanism_type')
            mechanism_type = QoSMechanismType(mechanism_type_str)
            priority = request.form.get('priority', 0)
            bandwidth_percent = request.form.get('bandwidth_percent')
            bandwidth_kbps = request.form.get('bandwidth_kbps')
            is_priority = request.form.get('is_priority') == 'on'
            
            if bandwidth_percent and bandwidth_percent.isdigit():
                bandwidth_percent = float(bandwidth_percent)
            else:
                bandwidth_percent = None
                
            if bandwidth_kbps and bandwidth_kbps.isdigit():
                bandwidth_kbps = int(bandwidth_kbps)
            else:
                bandwidth_kbps = None
            
            # WRED parameters
            wred_min = request.form.get('wred_min_threshold')
            wred_max = request.form.get('wred_max_threshold')
            wred_prob = request.form.get('wred_max_probability')
            
            if wred_min and wred_min.isdigit():
                wred_min = int(wred_min)
            else:
                wred_min = None
                
            if wred_max and wred_max.isdigit():
                wred_max = int(wred_max)
            else:
                wred_max = None
                
            if wred_prob and wred_prob.replace('.', '', 1).isdigit():
                wred_prob = float(wred_prob)
            else:
                wred_prob = None
            
            add_policy_entry(
                policy_map_id=policy_map_id,
                class_map_id=class_map_id,
                mechanism_type=mechanism_type,
                priority=priority,
                bandwidth_percent=bandwidth_percent,
                bandwidth_kbps=bandwidth_kbps,
                is_priority=is_priority,
                wred_min_threshold=wred_min,
                wred_max_threshold=wred_max,
                wred_max_probability=wred_prob
            )
            
            flash(f"QoS policy '{policy_map_name}' created successfully.")
            return redirect(url_for('MarkEngineView.rules'))
        
        # GET request - show form
        # Format devices
        devices_data = []
        for device in db.session.query(Device).all():
            devices_data.append({
                'id': device.id,
                'ip': device.ip,
                'connection_status': "Active" if device.connection and device.connection.status == 1 else "Inactive",
                'snmp_status': "Active" if device.snmp and device.snmp.status == 1 else "Inactive",
                'icmp_status': "Active" if device.icmp and device.icmp.status == 1 else "Inactive"
            })
            
        return self.render_template(
            "mark_engine_wizard.html",
            devices=devices_data,
            qos_mechanisms=[m.value for m in QoSMechanismType]
        )

    @expose("/stats")
    @has_access
    def stats(self):
        # Format devices
        devices_data = []
        for device in db.session.query(Device).all():
            devices_data.append({
                'id': device.id,
                'ip': device.ip,
                'connection_status': "Active" if device.connection and device.connection.status == 1 else "Inactive",
                'snmp_status': "Active" if device.snmp and device.snmp.status == 1 else "Inactive",
                'icmp_status': "Active" if device.icmp and device.icmp.status == 1 else "Inactive"
            })
            
        return self.render_template(
            "mark_engine_stats.html",
            devices=devices_data
        )
        
    @expose("/api/bandwidth/<int:interface_id>")
    @has_access
    def bandwidth_data(self, interface_id):
        hours = request.args.get('hours', 24, type=int)
        data = get_interface_bandwidth_history(interface_id, hours)
        return jsonify(data)


class DropEngineView(BaseView):
    route_base = "/dropengine"
    default_view = "rules"

    @expose("/rules")
    @has_access
    def rules(self):
        # Format policy maps
        policy_maps_data = []
        for pm in db.session.query(PolicyMap).all():
            policy_maps_data.append({
                'id': pm.id,
                'name': pm.name,
                'description': pm.description,
                'created_at': pm.created_at,
                'updated_at': pm.updated_at
            })
        
        # Format policy entries with WRED mechanism
        policy_entries_data = []
        for pe in db.session.query(PolicyEntry).filter_by(mechanism_type=QoSMechanismType.WRED).all():
            policy_map_name = pe.policy_map.name if pe.policy_map else "Unknown"
            class_map_name = pe.class_map.name if pe.class_map else "Unknown"
            
            policy_entries_data.append({
                'id': pe.id,
                'policy_map_id': pe.policy_map_id,
                'policy_map_name': policy_map_name,
                'class_map_id': pe.class_map_id,
                'class_map_name': class_map_name,
                'wred_min_threshold': pe.wred_min_threshold,
                'wred_max_threshold': pe.wred_max_threshold,
                'wred_max_probability': pe.wred_max_probability
            })
        
        return self.render_template(
            "drop_engine_rules.html",
            policy_maps=policy_maps_data,
            policy_entries=policy_entries_data
        )

    @expose("/wizard", methods=["GET", "POST"])
    @has_access
    def wizard(self):
        if request.method == "POST":
            # Create WRED policy
            policy_map_name = request.form.get('policy_map_name')
            policy_map_desc = request.form.get('policy_map_desc')
            
            policy_map_id = create_policy_map(
                name=policy_map_name,
                description=policy_map_desc
            )
            
            # Get class map
            class_map_id = request.form.get('class_map_id')
            
            # WRED parameters
            wred_min = request.form.get('wred_min_threshold')
            wred_max = request.form.get('wred_max_threshold')
            wred_prob = request.form.get('wred_max_probability')
            
            if wred_min and wred_min.isdigit():
                wred_min = int(wred_min)
            else:
                wred_min = None
                
            if wred_max and wred_max.isdigit():
                wred_max = int(wred_max)
            else:
                wred_max = None
                
            if wred_prob and wred_prob.replace('.', '', 1).isdigit():
                wred_prob = float(wred_prob)
            else:
                wred_prob = None
            
            add_policy_entry(
                policy_map_id=policy_map_id,
                class_map_id=class_map_id,
                mechanism_type=QoSMechanismType.WRED,
                wred_min_threshold=wred_min,
                wred_max_threshold=wred_max,
                wred_max_probability=wred_prob
            )
            
            flash(f"WRED policy '{policy_map_name}' created successfully.")
            return redirect(url_for('DropEngineView.rules'))
        
        # GET request - show form
        # Format class maps
        class_maps_data = []
        for cm in db.session.query(ClassMap).all():
            traffic_class_name = cm.traffic_class.name if cm.traffic_class else "Unknown"
            class_maps_data.append({
                'id': cm.id,
                'name': cm.name,
                'description': cm.description,
                'traffic_class_name': traffic_class_name
            })
            
        return self.render_template(
            "drop_engine_wizard.html",
            class_maps=class_maps_data
        )

    @expose("/stats")
    @has_access
    def stats(self):
        # Format devices
        devices_data = []
        for device in db.session.query(Device).all():
            devices_data.append({
                'id': device.id,
                'ip': device.ip,
                'connection_status': "Active" if device.connection and device.connection.status == 1 else "Inactive",
                'snmp_status': "Active" if device.snmp and device.snmp.status == 1 else "Inactive",
                'icmp_status': "Active" if device.icmp and device.icmp.status == 1 else "Inactive"
            })
            
        return self.render_template(
            "drop_engine_stats.html",
            devices=devices_data
        )
        
    @expose("/api/drops/<int:interface_id>")
    @has_access
    def drop_data(self, interface_id):
        hours = request.args.get('hours', 24, type=int)
        data = get_interface_bandwidth_history(interface_id, hours)
        
        # Filter for drop-related stats (input and output errors)
        drop_data = []
        for stat in data:
            drop_data.append({
                'timestamp': stat['timestamp'],
                'input_errors': stat['input_errors'],
                'output_errors': stat['output_errors']
            })
            
        return jsonify(drop_data)


class DeviceManagementView(BaseView):
    route_base = "/devices"
    default_view = "list"

    @expose("/list")
    @has_access
    def list(self):
        # Get all devices directly from the database instead of using get_all_devices()
        devices = db.session.query(Device).all()
        
        # Format device information for the template
        devices_info = []
        for device in devices:
            # Get status values
            snmp_status = "green" if device.snmp and device.snmp.status == 1 else "red"
            ping_status = "green" if device.icmp and device.icmp.status == 1 else "red"
            ssh_status = "green" if device.connection and device.connection.status == 1 else "red"
            
            # Add formatted device info
            devices_info.append((
                device.id,
                device.ip,
                snmp_status,
                ping_status,
                ssh_status
            ))
        
        return self.render_template(
            "devices_list.html",
            devices_info=devices_info
        )

    @expose("/new", methods=["GET", "POST"])
    def new(self):
        if request.method == "POST":
            router_ip = request.form.get('router_ip')
            ssh_username = request.form.get('ssh_username')
            ssh_password = request.form.get('ssh_password')
            snmp_community = request.form.get('snmp_comm_str')
            interval = 3  # Default ping interval
            
            # Check ping status
            ping_status, _ = ping_ip(router_ip, interval)
            ssh_status = 0
            snmp_status = 0
            interface_list = []
            
            if ping_status == 1:
                try:
                    from libssh_phr.cisco import com as conn
                    port = 22  # Default SSH port
                    host = f"{router_ip} : {port}"
                    ssh = conn.ssh(host, ssh_username, ssh_password, "")
                    cmd_resp = ssh.send("conf t")
                    
                    if "Enter configuration commands, one per line. " in cmd_resp:
                        ssh_status = 1
                        interface_list = update_interfaces(router_ip, snmp_community)
                        if interface_list:
                            snmp_status = 1
                
                except ImportError:
                    flash("SSH library not available. SSH check skipped.")
                except Exception as e:
                    flash(f"Error connecting to device: {str(e)}")
            
            add_new_device(
                router_ip=router_ip,
                connections_type=2,  # SSH connection type
                ssh_username=ssh_username,
                ssh_password=ssh_password,
                ssh_status=ssh_status,
                snmp_version=2,  # Default SNMP v2
                snmp_community=snmp_community,
                snmp_status=snmp_status,
                interval=interval,
                ping_status=ping_status,
                interfaces_list=interface_list
            )
            
            flash(f"Device {router_ip} added successfully.")
            return redirect(url_for('DeviceManagementView.list'))
        
        return self.render_template("devices_new.html")

    @expose("/<int:device_id>/interfaces")
    @has_access
    def interfaces(self, device_id):
        interfaces = get_device_interfaces(device_id)
        device_ip = get_ip_by_device_id(device_id)
        
        # Collect latest bandwidth stats
        try:
            collect_interface_bandwidth_stats(device_id)
        except Exception as e:
            flash(f"Error collecting bandwidth stats: {str(e)}")
        
        # Get interface details with policies
        interface_details = []
        for interface_id, device_id, ifname in interfaces:
            policies = get_interface_policies(interface_id)
            interface_details.append({
                'id': interface_id,
                'device_id': device_id,
                'name': ifname,
                'policies': policies
            })
        
        # Get available policy maps for applying to interfaces
        policy_maps = []
        for policy_map in db.session.query(PolicyMap).all():
            policy_maps.append({
                'id': policy_map.id,
                'name': policy_map.name
            })
        
        return self.render_template(
            "devices_interfaces.html",
            interfaces=interface_details,
            device_id=device_id,
            device_ip=device_ip,
            policy_maps=policy_maps
        )
        
    @expose("/<int:device_id>/interfaces/<int:interface_id>/apply_policy", methods=["POST"])
    @has_access
    def apply_policy(self, device_id, interface_id):
        policy_map_id = request.form.get('policy_map_id')
        direction = request.form.get('direction')
        
        if not policy_map_id or not direction:
            flash("Policy map and direction are required.")
            return redirect(url_for('DeviceManagementView.interfaces', device_id=device_id))
        
        try:
            apply_policy_to_interface(interface_id, int(policy_map_id), direction)
            flash("Policy applied successfully.")
        except Exception as e:
            flash(f"Error applying policy: {str(e)}")
            
        return redirect(url_for('DeviceManagementView.interfaces', device_id=device_id))
        
    @expose("/<int:device_id>/interfaces/<int:interface_id>/remove_policy", methods=["POST"])
    @has_access
    def remove_policy(self, device_id, interface_id):
        policy_map_id = request.form.get('policy_map_id')
        direction = request.form.get('direction')
        
        if not policy_map_id or not direction:
            flash("Policy map and direction are required.")
            return redirect(url_for('DeviceManagementView.interfaces', device_id=device_id))
        
        try:
            remove_policy_from_interface(interface_id, int(policy_map_id), direction)
            flash("Policy removed successfully.")
        except Exception as e:
            flash(f"Error removing policy: {str(e)}")
            
        return redirect(url_for('DeviceManagementView.interfaces', device_id=device_id))
        
    @expose("/<int:device_id>/bandwidth")
    @has_access
    def bandwidth(self, device_id):
        device = db.session.query(Device).get(device_id)
        if not device:
            flash("Device not found.")
            return redirect(url_for('DeviceManagementView.list'))
            
        # Get hours parameter from request
        hours = request.args.get('hours', 24, type=int)
        
        # Format device data
        device_data = {
            'id': device.id,
            'ip': device.ip,
            'connection_status': "Active" if device.connection and device.connection.status == 1 else "Inactive",
            'snmp_status': "Active" if device.snmp and device.snmp.status == 1 else "Inactive",
            'icmp_status': "Active" if device.icmp and device.icmp.status == 1 else "Inactive"
        }
        
        # Get interfaces with bandwidth stats
        interfaces_data = []
        for interface in device.interfaces.all():
            # Get bandwidth history for the specified time period
            stats = get_interface_bandwidth_history(interface.id, hours)
            
            # Format interface data
            interface_data = {
                'id': interface.id,
                'ifname': interface.ifname,
                'description': interface.description,
                'bandwidth': interface.bandwidth,
                'is_active': interface.is_active,
                'bandwidth_stats': []
            }
            
            # Add formatted bandwidth stats
            for stat_dict in stats:
                interface_data['bandwidth_stats'].append({
                    'timestamp': stat_dict['timestamp'],
                    'input_rate_kbps': stat_dict['input_rate_kbps'],
                    'output_rate_kbps': stat_dict['output_rate_kbps'],
                    'input_packets': stat_dict['input_packets'],
                    'output_packets': stat_dict['output_packets'],
                    'input_errors': stat_dict['input_errors'],
                    'output_errors': stat_dict['output_errors']
                })
            
            interfaces_data.append(interface_data)
        
        return self.render_template(
            "device_bandwidth.html",
            device=device_data,
            interfaces=interfaces_data,
            hours=hours
        )
        
    @expose("/<int:device_id>/bandwidth_chart/<int:interface_id>")
    @has_access
    def bandwidth_chart(self, device_id, interface_id):
        """Generate a bandwidth chart for an interface"""
        from io import BytesIO
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.dates import DateFormatter
        import numpy as np
        from flask import send_file
        
        # Get hours parameter from request
        hours = request.args.get('hours', 24, type=int)
        
        # Get bandwidth history for the specified time period
        stats = get_interface_bandwidth_history(interface_id, hours)
        
        if not stats:
            # Create a simple "No data available" image
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, 'No bandwidth data available', 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=14)
            ax.set_axis_off()
            
            # Save to BytesIO
            img_io = BytesIO()
            plt.savefig(img_io, format='png', bbox_inches='tight')
            img_io.seek(0)
            plt.close(fig)
            
            return send_file(img_io, mimetype='image/png')
        
        # Extract data
        timestamps = [datetime.fromisoformat(stat['timestamp']) for stat in stats]
        input_rates = [stat['input_rate_kbps'] / 1000 for stat in stats]  # Convert to Mbps
        output_rates = [stat['output_rate_kbps'] / 1000 for stat in stats]  # Convert to Mbps
        
        # Create figure and plot data
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(timestamps, input_rates, 'b-', label='Input (Mbps)')
        ax.plot(timestamps, output_rates, 'r-', label='Output (Mbps)')
        
        # Format the plot
        ax.set_title('Bandwidth Usage')
        ax.set_xlabel('Time')
        ax.set_ylabel('Bandwidth (Mbps)')
        ax.grid(True)
        ax.legend()
        
        # Format x-axis dates
        date_format = DateFormatter('%H:%M:%S')
        ax.xaxis.set_major_formatter(date_format)
        fig.autofmt_xdate()
        
        # Save to BytesIO
        img_io = BytesIO()
        plt.savefig(img_io, format='png', bbox_inches='tight')
        img_io.seek(0)
        plt.close(fig)
        
        return send_file(img_io, mimetype='image/png')


class ConnectionModelView(ModelView):
    datamodel = SQLAInterface(Connection)
    list_columns = ['id', 'type', 'status', 'username']
    add_columns = ['type', 'status', 'username', 'password']
    edit_columns = ['type', 'status', 'username', 'password']
    label_columns = {
        'type': 'Connection Type',
        'status': 'Status',
        'username': 'Username',
        'password': 'Password'
    }
    
    def format_type(self, item):
        """Format connection type"""
        if item.type == 1:
            return "Telnet"
        elif item.type == 2:
            return "SSH"
        else:
            return f"Unknown ({item.type})"
                
    def format_status(self, item):
        """Format connection status"""
        if item.status == 1:
            return "Active"
        elif item.status == 0:
            return "Inactive"
        else:
            return f"Unknown ({item.status})"

class SNMPModelView(ModelView):
    datamodel = SQLAInterface(SNMP)
    list_columns = ['id', 'status', 'version', 'comm_key']
    add_columns = ['status', 'version', 'comm_key']
    edit_columns = ['status', 'version', 'comm_key']
    label_columns = {
        'status': 'Status',
        'version': 'Version',
        'comm_key': 'Community String'
    }
    
    def format_status(self, item):
        """Format SNMP status"""
        if item.status == 1:
            return "Active"
        elif item.status == 0:
            return "Inactive"
        else:
            return f"Unknown ({item.status})"
                
    def format_version(self, item):
        """Format SNMP version"""
        if item.version == 1:
            return "v1"
        elif item.version == 2:
            return "v2c"
        elif item.version == 3:
            return "v3"
        else:
            return f"Unknown ({item.version})"

class ICMPModelView(ModelView):
    datamodel = SQLAInterface(ICMP)
    list_columns = ['id', 'status', 'avg_ping', 'interval_atmp']
    add_columns = ['status', 'avg_ping', 'interval_atmp']
    edit_columns = ['status', 'avg_ping', 'interval_atmp']
    label_columns = {
        'status': 'Status',
        'avg_ping': 'Average Ping (ms)',
        'interval_atmp': 'Ping Interval'
    }
    
    def format_status(self, item):
        """Format ICMP status"""
        if item.status == 1:
            return "Active"
        elif item.status == 0:
            return "Inactive"
        else:
            return f"Unknown ({item.status})"

class InterfaceModelView(ModelView):
    datamodel = SQLAInterface(Interface)
    list_columns = ['id', 'device', 'ifname', 'description', 'bandwidth', 'is_active']
    add_columns = ['device', 'ifname', 'description', 'bandwidth', 'is_active']
    edit_columns = ['device', 'ifname', 'description', 'bandwidth', 'is_active']
    # We'll set related_views after PolicyApplicationModelView and BandwidthStatModelView are defined
    label_columns = {
        'device': 'Device',
        'ifname': 'Interface Name',
        'description': 'Description',
        'bandwidth': 'Bandwidth (Kbps)',
        'is_active': 'Active'
    }
    
    def format_device(self, item):
        """Format device display"""
        if item.device:
            return item.device.ip
        else:
            return "Unknown"

class PolicyApplicationModelView(ModelView):
    datamodel = SQLAInterface(PolicyApplication)
    list_columns = ['id', 'interface', 'policy_map', 'direction', 'is_active', 'applied_at']
    add_columns = ['interface', 'policy_map', 'direction', 'is_active']
    edit_columns = ['interface', 'policy_map', 'direction', 'is_active']
    label_columns = {
        'interface': 'Interface',
        'policy_map': 'Policy Map',
        'direction': 'Direction',
        'is_active': 'Active',
        'applied_at': 'Applied At'
    }
    
    def format_interface(self, item):
        """Format interface display"""
        if item.interface:
            return item.interface.ifname
        else:
            return "Unknown"
                
    def format_policy_map(self, item):
        """Format policy map display"""
        if item.policy_map:
            return item.policy_map.name
        else:
            return "Unknown"

class DeviceModelView(ModelView):
    datamodel = SQLAInterface(Device)
    list_columns = ['id', 'ip', 'connection', 'snmp', 'icmp']
    related_views = [ConnectionModelView, SNMPModelView, ICMPModelView, InterfaceModelView]
    add_columns = ['ip', 'connection', 'snmp', 'icmp']
    edit_columns = ['ip', 'connection', 'snmp', 'icmp']
    label_columns = {
        'ip': 'IP Address',
        'connection': 'Connection Status',
        'snmp': 'SNMP Status',
        'icmp': 'ICMP Status'
    }
    
    def format_connection(self, item):
        """Format connection status display"""
        if item.connection:
            return "Active" if item.connection.status == 1 else "Inactive"
        else:
            return "Not Configured"
                
    def format_snmp(self, item):
        """Format SNMP status display"""
        if item.snmp:
            return "Active" if item.snmp.status == 1 else "Inactive"
        else:
            return "Not Configured"
                
    def format_icmp(self, item):
        """Format ICMP status display"""
        if item.icmp:
            return "Active" if item.icmp.status == 1 else "Inactive"
        else:
            return "Not Configured"

# QoS Model Views
class TrafficClassModelView(ModelView):
    datamodel = SQLAInterface(TrafficClass)
    list_columns = ['id', 'name', 'description', 'dscp_value']
    add_columns = ['name', 'description', 'dscp_value']
    edit_columns = ['name', 'description', 'dscp_value']
    # We'll set related_views after ClassMapModelView is defined
    label_columns = {
        'name': 'Traffic Class',
        'description': 'Description',
        'dscp_value': 'DSCP Value'
    }

class ClassMapModelView(ModelView):
    datamodel = SQLAInterface(ClassMap)
    list_columns = ['id', 'name', 'description', 'traffic_class']
    add_columns = ['name', 'description', 'match_criteria', 'traffic_class']
    edit_columns = ['name', 'description', 'match_criteria', 'traffic_class']
    # We'll set related_views after PolicyEntryModelView is defined
    label_columns = {
        'name': 'Class Map',
        'description': 'Description',
        'traffic_class': 'Traffic Class',
        'match_criteria': 'Match Criteria'
    }
    
    def format_traffic_class(self, item):
        """Format traffic class display"""
        if item.traffic_class:
            return item.traffic_class.name
        else:
            return "Unknown"

class PolicyMapModelView(ModelView):
    datamodel = SQLAInterface(PolicyMap)
    list_columns = ['id', 'name', 'description', 'created_at', 'updated_at']
    add_columns = ['name', 'description']
    edit_columns = ['name', 'description']
    # We'll set related_views after PolicyEntryModelView is defined
    label_columns = {
        'name': 'Policy Name',
        'description': 'Description',
        'created_at': 'Created',
        'updated_at': 'Last Updated'
    }

class PolicyEntryModelView(ModelView):
    datamodel = SQLAInterface(PolicyEntry)
    list_columns = ['id', 'policy_map', 'class_map', 'mechanism_type', 'priority']
    add_columns = [
        'policy_map', 'class_map', 'mechanism_type', 'priority',
        'bandwidth_percent', 'bandwidth_kbps', 'is_priority',
        'wred_min_threshold', 'wred_max_threshold', 'wred_max_probability'
    ]
    edit_columns = [
        'policy_map', 'class_map', 'mechanism_type', 'priority',
        'bandwidth_percent', 'bandwidth_kbps', 'is_priority',
        'wred_min_threshold', 'wred_max_threshold', 'wred_max_probability'
    ]
    label_columns = {
        'policy_map': 'Policy Map',
        'class_map': 'Class Map',
        'mechanism_type': 'QoS Mechanism',
        'priority': 'Priority',
        'bandwidth_percent': 'Bandwidth %',
        'bandwidth_kbps': 'Bandwidth (Kbps)',
        'is_priority': 'Priority Queue',
        'wred_min_threshold': 'WRED Min Threshold',
        'wred_max_threshold': 'WRED Max Threshold',
        'wred_max_probability': 'WRED Max Probability'
    }
    
    def format_policy_map(self, item):
        """Format policy map display"""
        if item.policy_map:
            return item.policy_map.name
        else:
            return "Unknown"
                
    def format_class_map(self, item):
        """Format class map display"""
        if item.class_map:
            return item.class_map.name
        else:
            return "Unknown"

class PolicyApplicationModelView(ModelView):
    datamodel = SQLAInterface(PolicyApplication)
    list_columns = ['id', 'interface', 'policy_map', 'direction', 'is_active', 'applied_at']
    add_columns = ['interface', 'policy_map', 'direction', 'is_active']
    edit_columns = ['interface', 'policy_map', 'direction', 'is_active']
    
    def format_interface(self, item):
        """Format interface display"""
        if item.interface:
            return item.interface.ifname
        else:
            return "Unknown"
                
    def format_policy_map(self, item):
        """Format policy map display"""
        if item.policy_map:
            return item.policy_map.name
        else:
            return "Unknown"

class BandwidthStatModelView(ModelView):
    datamodel = SQLAInterface(BandwidthStat)
    list_columns = [
        'id', 'interface', 'timestamp', 'input_rate_kbps', 
        'output_rate_kbps', 'input_errors', 'output_errors'
    ]
    search_columns = ['interface', 'timestamp']
    base_order = ('timestamp', 'desc')
    label_columns = {
        'interface': 'Interface',
        'timestamp': 'Time',
        'input_rate_kbps': 'Input Rate (Kbps)',
        'output_rate_kbps': 'Output Rate (Kbps)',
        'input_errors': 'Input Errors',
        'output_errors': 'Output Errors',
        'input_packets': 'Input Packets',
        'output_packets': 'Output Packets'
    }
    
    def format_interface(self, item):
        """Format interface display"""
        if item.interface:
            return item.interface.ifname
        elif hasattr(item, 'interface_id'):
            interface = db.session.query(Interface).get(item.interface_id)
            if interface:
                return interface.ifname
            else:
                return f"Interface #{item.interface_id}"
        else:
            return "Unknown"

# Now that all model views are defined, set related_views for classes that had circular dependencies
InterfaceModelView.related_views = [PolicyApplicationModelView, BandwidthStatModelView]
ClassMapModelView.related_views = [PolicyEntryModelView]
TrafficClassModelView.related_views = [ClassMapModelView]
PolicyMapModelView.related_views = [PolicyEntryModelView, PolicyApplicationModelView]

# Create menu categories and links
appbuilder.add_link("Mark Engine", href="/markengine/rules", category="QoS Configuration", icon="fa-tag")
appbuilder.add_link("Drop Engine", href="/dropengine/rules", category="QoS Configuration", icon="fa-trash-alt")
appbuilder.add_link("Device Management", href="/devices/list", category="Devices", icon="fa-server")

# Register views
appbuilder.add_view_no_menu(MarkEngineView)
appbuilder.add_view_no_menu(DropEngineView)
appbuilder.add_view_no_menu(DeviceManagementView)

# Device-related views
appbuilder.add_view(
    ConnectionModelView,
    "Connections",
    icon="fa-plug",
    category="Devices"
)

appbuilder.add_view(
    SNMPModelView,
    "SNMP Configs", 
    icon="fa-shield",
    category="Devices"
)

appbuilder.add_view(
    ICMPModelView,
    "ICMP Configs",
    icon="fa-bullseye",
    category="Devices"
)

appbuilder.add_view(
    DeviceModelView,
    "Devices",
    icon="fa-server",
    category="Devices"
)

appbuilder.add_view(
    InterfaceModelView,
    "Interfaces",
    icon="fa-network-wired",
    category="Devices"
)

# QoS-related views
appbuilder.add_view(
    TrafficClassModelView,
    "Traffic Classes",
    icon="fa-tags",
    category="QoS Configuration"
)

appbuilder.add_view(
    ClassMapModelView,
    "Class Maps",
    icon="fa-filter",
    category="QoS Configuration"
)

appbuilder.add_view(
    PolicyMapModelView,
    "Policy Maps",
    icon="fa-map",
    category="QoS Configuration"
)

appbuilder.add_view(
    PolicyEntryModelView,
    "Policy Entries",
    icon="fa-list",
    category="QoS Configuration"
)

appbuilder.add_view(
    PolicyApplicationModelView,
    "Policy Applications",
    icon="fa-check-square",
    category="QoS Configuration"
)

appbuilder.add_view(
    BandwidthStatModelView,
    "Bandwidth Statistics",
    icon="fa-bar-chart",
    category="Monitoring"
)

@appbuilder.app.errorhandler(404)
def page_not_found(e):
    return (
        render_template(
            "404.html", base_template=appbuilder.base_template, appbuilder=appbuilder
        ),
        404,
    )
db.create_all()
