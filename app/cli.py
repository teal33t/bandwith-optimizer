import click
from flask.cli import with_appcontext
from app import db
from app.models import (
    Device, Interface, Connection, SNMP, ICMP,
    TrafficClass, ClassMap, PolicyMap, PolicyEntry, 
    PolicyApplication, BandwidthStat, QoSMechanismType
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

def register_commands(app):
    """Register CLI commands with the Flask application"""
    app.cli.add_command(fake_add_command)
    app.cli.add_command(fake_remove_command)
