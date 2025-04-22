import os
import sys
import django
from decimal import Decimal

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'traffic_violation_system.settings')
django.setup()

from traffic_violation_system.models import ViolationType

# Define the initial violation types and amounts
VIOLATION_TYPES = [
    # Licensing Violations
    {
        'name': 'Unlicensed Driver',
        'description': 'Driving without a valid driver\'s license',
        'amount': Decimal('1000.00'),
        'category': 'LICENSING'
    },
    {
        'name': 'No License',
        'description': 'Failure to carry driver\'s license',
        'amount': Decimal('500.00'),
        'category': 'LICENSING'
    },
    {
        'name': 'Expired License',
        'description': 'Driving with an expired driver\'s license',
        'amount': Decimal('750.00'),
        'category': 'LICENSING'
    },
    
    # Registration Violations
    {
        'name': 'Unregistered MV',
        'description': 'Operating an unregistered motor vehicle',
        'amount': Decimal('1000.00'),
        'category': 'REGISTRATION'
    },
    {
        'name': 'Expired OR/CR',
        'description': 'Operating with expired registration',
        'amount': Decimal('750.00'),
        'category': 'REGISTRATION'
    },
    {
        'name': 'No Plate',
        'description': 'Operating a vehicle without proper license plates',
        'amount': Decimal('500.00'),
        'category': 'REGISTRATION'
    },
    {
        'name': 'Defective Lights',
        'description': 'Operating a vehicle with no or defective lights',
        'amount': Decimal('300.00'),
        'category': 'REGISTRATION'
    },
    {
        'name': 'Defective Muffler',
        'description': 'Operating a vehicle with defective muffler',
        'amount': Decimal('300.00'),
        'category': 'REGISTRATION'
    },
    {
        'name': 'Dilapidated',
        'description': 'Operating a dilapidated motorcab',
        'amount': Decimal('500.00'),
        'category': 'REGISTRATION'
    },
    
    # Dimension Violations
    {
        'name': 'Overloading',
        'description': 'Carrying load exceeding the authorized capacity',
        'amount': Decimal('800.00'),
        'category': 'DIMENSION'
    },
    {
        'name': 'Permitting Hitching',
        'description': 'Permitting hitching or overloading passengers',
        'amount': Decimal('500.00'),
        'category': 'DIMENSION'
    },
    
    # Franchise Violations
    {
        'name': 'No Permit',
        'description': 'No Mayor\'s Permit, MTOP, POP, or PDP',
        'amount': Decimal('1000.00'),
        'category': 'FRANCHISE'
    },
    {
        'name': 'Colorum Operation',
        'description': 'Operating a public utility vehicle without proper franchise',
        'amount': Decimal('2000.00'),
        'category': 'FRANCHISE'
    },
    
    # Other Violations
    {
        'name': 'Illegal Parking',
        'description': 'Illegal parking (DTS)',
        'amount': Decimal('500.00'),
        'category': 'OTHER'
    },
    {
        'name': 'Entering Prohibited Zones',
        'description': 'Entering areas designated as prohibited zones',
        'amount': Decimal('500.00'),
        'category': 'OTHER'
    },
    {
        'name': 'Obstruction',
        'description': 'Causing obstruction to traffic flow',
        'amount': Decimal('500.00'),
        'category': 'OTHER'
    },
    {
        'name': 'Refusal to Convey',
        'description': 'Refusal to convey to proper destination',
        'amount': Decimal('500.00'),
        'category': 'OTHER'
    },
    {
        'name': 'Discourteous Driver',
        'description': 'Discourteous driver conduct',
        'amount': Decimal('500.00'),
        'category': 'OTHER'
    },
    {
        'name': 'Overcharging',
        'description': 'Charging fare higher than the authorized rate',
        'amount': Decimal('500.00'),
        'category': 'OTHER'
    },
    {
        'name': 'DUI',
        'description': 'Driving under the influence of liquor/drugs',
        'amount': Decimal('2000.00'),
        'category': 'OTHER'
    },
    {
        'name': 'Reckless Driving',
        'description': 'Driving in a reckless or careless manner',
        'amount': Decimal('1000.00'),
        'category': 'OTHER'
    },
]

def initialize_violation_types():
    # Count existing violation types
    existing_count = ViolationType.objects.count()
    if existing_count > 0:
        print(f"There are already {existing_count} violation types in the database.")
        user_input = input("Do you want to continue and add more violation types? (y/n): ")
        if user_input.lower() != 'y':
            print("Initialization cancelled.")
            return
    
    # Create violation types
    created_count = 0
    skipped_count = 0
    
    for vtype in VIOLATION_TYPES:
        # Check if violation type already exists
        if ViolationType.objects.filter(name=vtype['name']).exists():
            print(f"Skipping existing violation type: {vtype['name']}")
            skipped_count += 1
            continue
        
        # Create new violation type
        ViolationType.objects.create(
            name=vtype['name'],
            description=vtype['description'],
            amount=vtype['amount'],
            category=vtype['category']
        )
        created_count += 1
        print(f"Created violation type: {vtype['name']}")
    
    print(f"\nInitialization complete: {created_count} violation types created, {skipped_count} skipped.")

if __name__ == "__main__":
    print("Initializing violation types...")
    initialize_violation_types() 