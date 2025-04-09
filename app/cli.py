import click
import os
import time
from datetime import datetime
from flask.cli import with_appcontext
from app import db
from app.models import (
    Device, Interface, Connection, SNMP, ICMP,
    TrafficClass, ClassMap, PolicyMap, PolicyEntry, 
    PolicyApplication, BandwidthStat, QoSMechanismType
)
from app.utils import (
    ping_ip, decrypt_sensitive_data, collect_interface_bandwidth_stats,
    get_all_devices
)

@click.command("fake-add")
@with_appcontext
def fake_add_command():
    """Add fake data to the database"""
    from load_fake_data import create_fake_data
    create_fake_data()

@click.command("fake-remove")
@with_appcontext
def fake_remove_command():
    """Remove all data from the database"""
    print("Removing all data from the database...")
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
    print("All data has been removed successfully!")

@click.command("collect-stats")
@click.option("--device-id", type=int, help="Collect stats for a specific device ID")
@click.option("--all", is_flag=True, default=True, help="Collect stats for all devices")
@click.option("--verbose", is_flag=True, help="Show detailed output")
@with_appcontext
def collect_stats_command(device_id, all, verbose):
    """Collect bandwidth statistics for all devices or a specific device"""
    start_time = time.time()
    success_count = 0
    failure_count = 0
    
    if device_id:
        # Collect stats for a specific device
        device = db.session.query(Device).get(device_id)
        if not device:
            click.echo(f"Error: Device with ID {device_id} not found.")
            return
            
        click.echo(f"Collecting bandwidth statistics for device {device.ip}...")
        try:
            result = collect_interface_bandwidth_stats(device.id)
            if result:
                success_count += 1
                click.echo(f"Successfully collected statistics for {device.ip}")
            else:
                failure_count += 1
                click.echo(f"Failed to collect statistics for {device.ip}")
        except Exception as e:
            failure_count += 1
            click.echo(f"Error collecting statistics for {device.ip}: {str(e)}")
    else:
        # Collect stats for all devices
        devices = db.session.query(Device).all()
        total_devices = len(devices)
        
        if total_devices == 0:
            click.echo("No devices found in the database.")
            return
            
        click.echo(f"Collecting bandwidth statistics for {total_devices} devices...")
        
        for i, device in enumerate(devices, 1):
            if verbose:
                click.echo(f"[{i}/{total_devices}] Processing {device.ip}...")
            
            try:
                result = collect_interface_bandwidth_stats(device.id)
                if result:
                    success_count += 1
                    if verbose:
                        click.echo(f"  ✓ Successfully collected statistics")
                else:
                    failure_count += 1
                    if verbose:
                        click.echo(f"  ✗ Failed to collect statistics")
            except Exception as e:
                failure_count += 1
                if verbose:
                    click.echo(f"  ✗ Error: {str(e)}")
    
    elapsed_time = time.time() - start_time
    click.echo(f"\nStatistics collection completed in {elapsed_time:.2f} seconds")
    click.echo(f"Success: {success_count}, Failures: {failure_count}")

@click.command("check-devices")
@click.option("--ping", is_flag=True, default=True, help="Check ICMP connectivity")
@click.option("--ssh", is_flag=True, default=True, help="Check SSH connectivity")
@click.option("--snmp", is_flag=True, default=True, help="Check SNMP connectivity")
@click.option("--timeout", type=int, default=5, help="Connection timeout in seconds")
@click.option("--verbose", is_flag=True, help="Show detailed output")
@with_appcontext
def check_devices_command(ping, ssh, snmp, timeout, verbose):
    """Verify connectivity to all devices"""
    start_time = time.time()
    devices = db.session.query(Device).all()
    total_devices = len(devices)
    
    if total_devices == 0:
        click.echo("No devices found in the database.")
        return
        
    click.echo(f"Checking connectivity for {total_devices} devices...")
    
    ping_success = 0
    ssh_success = 0
    snmp_success = 0
    
    for i, device in enumerate(devices, 1):
        if verbose:
            click.echo(f"\n[{i}/{total_devices}] Checking {device.ip}...")
        else:
            click.echo(f"Checking {device.ip}...", nl=False)
        
        # Check ICMP connectivity
        if ping:
            ping_status, _ = ping_ip(device.ip, 3)
            if ping_status == 1:
                ping_success += 1
                if verbose:
                    click.echo(f"  ✓ ICMP: Reachable")
            else:
                if verbose:
                    click.echo(f"  ✗ ICMP: Unreachable")
            
            # Update ICMP status in database
            if device.icmp:
                device.icmp.status = ping_status
                db.session.commit()
        
        # Check SSH connectivity
        if ssh and device.connection:
            ssh_status = 0
            try:
                from app.libssh_phr.cisco import com as conn
                ssh_username = device.connection.username
                ssh_password = decrypt_sensitive_data(device.connection.password)
                port = 22  # Default SSH port
                host = f"{device.ip}:{port}"
                
                # Set a timeout for SSH connection
                import socket
                socket.setdefaulttimeout(timeout)
                
                ssh = conn.ssh(host, ssh_username, ssh_password, "")
                cmd_resp = ssh.send("show version")
                
                if cmd_resp:
                    ssh_status = 1
                    ssh_success += 1
                    if verbose:
                        click.echo(f"  ✓ SSH: Connected")
                else:
                    if verbose:
                        click.echo(f"  ✗ SSH: Failed to execute command")
                
                ssh.close()
            except Exception as e:
                if verbose:
                    click.echo(f"  ✗ SSH: {str(e)}")
            
            # Update SSH status in database
            device.connection.status = ssh_status
            db.session.commit()
        
        # Check SNMP connectivity
        if snmp and device.snmp:
            snmp_status = 0
            try:
                from pysnmp.hlapi import (
                    SnmpEngine, CommunityData, UdpTransportTarget,
                    ContextData, ObjectType, ObjectIdentity, getCmd
                )
                
                community = decrypt_sensitive_data(device.snmp.comm_key)
                
                # Try to get sysDescr (a basic SNMP query)
                error_indication, error_status, error_index, var_binds = next(
                    getCmd(
                        SnmpEngine(),
                        CommunityData(community),
                        UdpTransportTarget((device.ip, 161), timeout=timeout),
                        ContextData(),
                        ObjectType(ObjectIdentity('1.3.6.1.2.1.1.1.0'))  # sysDescr
                    )
                )
                
                if error_indication or error_status:
                    if verbose:
                        click.echo(f"  ✗ SNMP: {error_indication or error_status}")
                else:
                    snmp_status = 1
                    snmp_success += 1
                    if verbose:
                        click.echo(f"  ✓ SNMP: Responding")
            except Exception as e:
                if verbose:
                    click.echo(f"  ✗ SNMP: {str(e)}")
            
            # Update SNMP status in database
            device.snmp.status = snmp_status
            db.session.commit()
        
        if not verbose:
            status_icons = []
            if ping:
                status_icons.append("✓" if device.icmp and device.icmp.status == 1 else "✗")
            if ssh:
                status_icons.append("✓" if device.connection and device.connection.status == 1 else "✗")
            if snmp:
                status_icons.append("✓" if device.snmp and device.snmp.status == 1 else "✗")
            
            click.echo(f" [{' '.join(status_icons)}]")
    
    elapsed_time = time.time() - start_time
    click.echo(f"\nConnectivity check completed in {elapsed_time:.2f} seconds")
    
    if ping:
        click.echo(f"ICMP: {ping_success}/{total_devices} devices reachable")
    if ssh:
        click.echo(f"SSH: {ssh_success}/{total_devices} devices accessible")
    if snmp:
        click.echo(f"SNMP: {snmp_success}/{total_devices} devices responding")

@click.command("export-config")
@click.option("--format", type=click.Choice(["pdf", "html", "txt"]), default="pdf", help="Export format")
@click.option("--output", type=str, help="Output file path")
@click.option("--device-id", type=int, help="Export config for a specific device")
@with_appcontext
def export_config_command(format, output, device_id):
    """Export configuration report"""
    # Determine output filename if not specified
    if not output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if device_id:
            device = db.session.query(Device).get(device_id)
            if not device:
                click.echo(f"Error: Device with ID {device_id} not found.")
                return
            filename = f"config_report_{device.ip}_{timestamp}.{format}"
        else:
            filename = f"config_report_{timestamp}.{format}"
        
        # Create reports directory if it doesn't exist
        os.makedirs("reports", exist_ok=True)
        output = os.path.join("reports", filename)
    
    click.echo(f"Generating {format.upper()} configuration report...")
    
    # Get devices data
    if device_id:
        devices = [db.session.query(Device).get(device_id)]
        if not devices[0]:
            click.echo(f"Error: Device with ID {device_id} not found.")
            return
    else:
        devices = db.session.query(Device).all()
    
    if not devices:
        click.echo("No devices found in the database.")
        return
    
    # Generate report based on format
    if format == "pdf":
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            
            doc = SimpleDocTemplate(output, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []
            
            # Title
            title = Paragraph("QoS Bandwidth Optimizer Configuration Report", styles['Title'])
            elements.append(title)
            elements.append(Spacer(1, 12))
            
            # Date
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            date = Paragraph(f"Generated on: {date_str}", styles['Normal'])
            elements.append(date)
            elements.append(Spacer(1, 24))
            
            # Devices table
            devices_data = [['ID', 'IP Address', 'SSH Status', 'SNMP Status', 'ICMP Status']]
            for device in devices:
                ssh_status = "Active" if device.connection and device.connection.status == 1 else "Inactive"
                snmp_status = "Active" if device.snmp and device.snmp.status == 1 else "Inactive"
                icmp_status = "Active" if device.icmp and device.icmp.status == 1 else "Inactive"
                
                devices_data.append([
                    str(device.id),
                    device.ip,
                    ssh_status,
                    snmp_status,
                    icmp_status
                ])
            
            devices_table = Table(devices_data, colWidths=[40, 100, 80, 80, 80])
            devices_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(Paragraph("Devices", styles['Heading2']))
            elements.append(Spacer(1, 6))
            elements.append(devices_table)
            elements.append(Spacer(1, 24))
            
            # For each device, add QoS policies
            for device in devices:
                elements.append(Paragraph(f"Device: {device.ip}", styles['Heading3']))
                elements.append(Spacer(1, 6))
                
                # Interfaces and policies
                for interface in device.interfaces:
                    elements.append(Paragraph(f"Interface: {interface.ifname}", styles['Heading4']))
                    elements.append(Spacer(1, 3))
                    
                    policies = db.session.query(PolicyApplication).filter_by(
                        interface_id=interface.id, is_active=True
                    ).all()
                    
                    if policies:
                        policy_data = [['Policy Name', 'Direction', 'Applied At']]
                        for policy in policies:
                            policy_map = db.session.query(PolicyMap).get(policy.policy_map_id)
                            if policy_map:
                                applied_at = policy.applied_at.strftime("%Y-%m-%d %H:%M:%S") if policy.applied_at else "Unknown"
                                policy_data.append([
                                    policy_map.name,
                                    policy.direction,
                                    applied_at
                                ])
                        
                        policy_table = Table(policy_data, colWidths=[150, 80, 150])
                        policy_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black)
                        ]))
                        
                        elements.append(policy_table)
                    else:
                        elements.append(Paragraph("No active policies", styles['Normal']))
                    
                    elements.append(Spacer(1, 12))
                
                elements.append(Spacer(1, 24))
            
            # Build the PDF
            doc.build(elements)
            click.echo(f"PDF report generated successfully: {output}")
            
        except ImportError:
            click.echo("Error: ReportLab library is required for PDF export.")
            click.echo("Install it with: pip install reportlab")
            return
        except Exception as e:
            click.echo(f"Error generating PDF report: {str(e)}")
            return
    
    elif format == "html":
        try:
            with open(output, 'w') as f:
                f.write("""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>QoS Bandwidth Optimizer Configuration Report</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 20px; }
                        h1 { color: #333366; }
                        h2 { color: #336699; margin-top: 30px; }
                        h3 { color: #339999; }
                        table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
                        th { background-color: #336699; color: white; text-align: left; padding: 8px; }
                        td { border: 1px solid #ddd; padding: 8px; }
                        tr:nth-child(even) { background-color: #f2f2f2; }
                    </style>
                </head>
                <body>
                    <h1>QoS Bandwidth Optimizer Configuration Report</h1>
                    <p>Generated on: %s</p>
                    
                    <h2>Devices</h2>
                    <table>
                        <tr>
                            <th>ID</th>
                            <th>IP Address</th>
                            <th>SSH Status</th>
                            <th>SNMP Status</th>
                            <th>ICMP Status</th>
                        </tr>
                """ % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                
                # Add devices
                for device in devices:
                    ssh_status = "Active" if device.connection and device.connection.status == 1 else "Inactive"
                    snmp_status = "Active" if device.snmp and device.snmp.status == 1 else "Inactive"
                    icmp_status = "Active" if device.icmp and device.icmp.status == 1 else "Inactive"
                    
                    f.write(f"""
                        <tr>
                            <td>{device.id}</td>
                            <td>{device.ip}</td>
                            <td>{ssh_status}</td>
                            <td>{snmp_status}</td>
                            <td>{icmp_status}</td>
                        </tr>
                    """)
                
                f.write("</table>")
                
                # For each device, add QoS policies
                for device in devices:
                    f.write(f"<h2>Device: {device.ip}</h2>")
                    
                    # Interfaces and policies
                    for interface in device.interfaces:
                        f.write(f"<h3>Interface: {interface.ifname}</h3>")
                        
                        policies = db.session.query(PolicyApplication).filter_by(
                            interface_id=interface.id, is_active=True
                        ).all()
                        
                        if policies:
                            f.write("""
                                <table>
                                    <tr>
                                        <th>Policy Name</th>
                                        <th>Direction</th>
                                        <th>Applied At</th>
                                    </tr>
                            """)
                            
                            for policy in policies:
                                policy_map = db.session.query(PolicyMap).get(policy.policy_map_id)
                                if policy_map:
                                    applied_at = policy.applied_at.strftime("%Y-%m-%d %H:%M:%S") if policy.applied_at else "Unknown"
                                    f.write(f"""
                                        <tr>
                                            <td>{policy_map.name}</td>
                                            <td>{policy.direction}</td>
                                            <td>{applied_at}</td>
                                        </tr>
                                    """)
                            
                            f.write("</table>")
                        else:
                            f.write("<p>No active policies</p>")
                
                f.write("</body></html>")
            
            click.echo(f"HTML report generated successfully: {output}")
            
        except Exception as e:
            click.echo(f"Error generating HTML report: {str(e)}")
            return
    
    elif format == "txt":
        try:
            with open(output, 'w') as f:
                f.write("QoS Bandwidth Optimizer Configuration Report\n")
                f.write("=" * 50 + "\n")
                f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("Devices\n")
                f.write("-" * 50 + "\n")
                f.write(f"{'ID':<5} {'IP Address':<15} {'SSH':<10} {'SNMP':<10} {'ICMP':<10}\n")
                f.write("-" * 50 + "\n")
                
                for device in devices:
                    ssh_status = "Active" if device.connection and device.connection.status == 1 else "Inactive"
                    snmp_status = "Active" if device.snmp and device.snmp.status == 1 else "Inactive"
                    icmp_status = "Active" if device.icmp and device.icmp.status == 1 else "Inactive"
                    
                    f.write(f"{device.id:<5} {device.ip:<15} {ssh_status:<10} {snmp_status:<10} {icmp_status:<10}\n")
                
                f.write("\n")
                
                # For each device, add QoS policies
                for device in devices:
                    f.write(f"\nDevice: {device.ip}\n")
                    f.write("=" * 30 + "\n")
                    
                    # Interfaces and policies
                    for interface in device.interfaces:
                        f.write(f"\n  Interface: {interface.ifname}\n")
                        f.write("  " + "-" * 25 + "\n")
                        
                        policies = db.session.query(PolicyApplication).filter_by(
                            interface_id=interface.id, is_active=True
                        ).all()
                        
                        if policies:
                            f.write(f"  {'Policy Name':<30} {'Direction':<10} {'Applied At':<20}\n")
                            f.write("  " + "-" * 60 + "\n")
                            
                            for policy in policies:
                                policy_map = db.session.query(PolicyMap).get(policy.policy_map_id)
                                if policy_map:
                                    applied_at = policy.applied_at.strftime("%Y-%m-%d %H:%M:%S") if policy.applied_at else "Unknown"
                                    f.write(f"  {policy_map.name:<30} {policy.direction:<10} {applied_at:<20}\n")
                        else:
                            f.write("  No active policies\n")
            
            click.echo(f"Text report generated successfully: {output}")
            
        except Exception as e:
            click.echo(f"Error generating text report: {str(e)}")
            return

def register_commands(app):
    """Register CLI commands with the Flask application"""
    app.cli.add_command(fake_add_command)
    app.cli.add_command(fake_remove_command)
    app.cli.add_command(collect_stats_command)
    app.cli.add_command(check_devices_command)
    app.cli.add_command(export_config_command)
