"""
Order Validators
Validates order data before creation and updates
"""
import re
from abc import ABC


class OrderValidator(ABC):
    """Validator for order creation and updates"""
    
    # Validation constants
    MIN_WEIGHT = 0.1  # kg
    MAX_WEIGHT = 200  # kg
    MIN_DISTANCE = 0.1  # km
    MAX_DISTANCE = 500  # km
    
    # Kenya coordinates bounds
    KENYA_LAT_MIN = -4.7
    KENYA_LAT_MAX = 4.9
    KENYA_LNG_MIN = 33.8
    KENYA_LNG_MAX = 41.9
    
    @staticmethod
    def validate_create_order(data: dict) -> tuple:
        """
        Validate order creation request data
        
        Args:
            data: Order request data
            
        Returns:
            tuple: (is_valid: bool, validated_data: dict, errors: dict)
        """
        errors = {}
        validated_data = {}
        
        # 1. VALIDATE REQUIRED FIELDS
        required_fields = {
            'pickup_lat': 'Pickup latitude is required',
            'pickup_lng': 'Pickup longitude is required',
            'pickup_address': 'Pickup address is required',
            'destination_lat': 'Destination latitude is required',
            'destination_lng': 'Destination longitude is required',
            'destination_address': 'Destination address is required',
            'weight_kg': 'Weight is required'
        }
        
        for field, error_msg in required_fields.items():
            if field not in data or data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
                errors[field] = error_msg
        
        if errors:
            return (False, {}, errors)
        
        # 2. VALIDATE COORDINATES
        try:
            pickup_lat = float(data['pickup_lat'])
            pickup_lng = float(data['pickup_lng'])
            destination_lat = float(data['destination_lat'])
            destination_lng = float(data['destination_lng'])
        except (ValueError, TypeError):
            errors['coordinates'] = 'Coordinates must be valid numbers (latitude -90 to 90, longitude -180 to 180)'
            return (False, {}, errors)
        
        # Check coordinate ranges
        if not (-90 <= pickup_lat <= 90):
            errors['pickup_lat'] = f'Pickup latitude must be between -90 and 90, got {pickup_lat}'
        if not (-180 <= pickup_lng <= 180):
            errors['pickup_lng'] = f'Pickup longitude must be between -180 and 180, got {pickup_lng}'
        if not (-90 <= destination_lat <= 90):
            errors['destination_lat'] = f'Destination latitude must be between -90 and 90, got {destination_lat}'
        if not (-180 <= destination_lng <= 180):
            errors['destination_lng'] = f'Destination longitude must be between -180 and 180, got {destination_lng}'
        
        # Optional: Check Kenya bounds
        if pickup_lat and (pickup_lat < OrderValidator.KENYA_LAT_MIN or pickup_lat > OrderValidator.KENYA_LAT_MAX):
            errors['pickup_location'] = 'Pickup location appears to be outside Kenya'
        if destination_lat and (destination_lat < OrderValidator.KENYA_LAT_MIN or destination_lat > OrderValidator.KENYA_LAT_MAX):
            errors['destination_location'] = 'Destination location appears to be outside Kenya'
        
        # 3. VALIDATE WEIGHT
        try:
            weight_kg = float(data['weight_kg'])
        except (ValueError, TypeError):
            errors['weight_kg'] = 'Weight must be a valid number in kilograms'
            return (False, {}, errors)
        
        if weight_kg < OrderValidator.MIN_WEIGHT:
            errors['weight_kg'] = f'Weight must be at least {OrderValidator.MIN_WEIGHT}kg'
        elif weight_kg > OrderValidator.MAX_WEIGHT:
            errors['weight_kg'] = f'Weight cannot exceed {OrderValidator.MAX_WEIGHT}kg'
        
        # 4. VALIDATE ADDRESSES
        pickup_address = (data.get('pickup_address') or '').strip()
        destination_address = (data.get('destination_address') or '').strip()
        
        if not pickup_address or len(pickup_address) < 3:
            errors['pickup_address'] = 'Pickup address must be at least 3 characters'
        elif len(pickup_address) > 500:
            errors['pickup_address'] = 'Pickup address must be less than 500 characters'
        
        if not destination_address or len(destination_address) < 3:
            errors['destination_address'] = 'Destination address must be at least 3 characters'
        elif len(destination_address) > 500:
            errors['destination_address'] = 'Destination address must be less than 500 characters'
        
        # 5. VALIDATE OPTIONAL PHONE NUMBERS (if provided)
        if 'pickup_phone' in data and data['pickup_phone']:
            if not OrderValidator._validate_phone(data['pickup_phone']):
                errors['pickup_phone'] = 'Invalid pickup phone number format'
        
        if 'destination_phone' in data and data['destination_phone']:
            if not OrderValidator._validate_phone(data['destination_phone']):
                errors['destination_phone'] = 'Invalid destination phone number format'
        
        # 6. VALIDATE OPTIONAL FIELDS
        if 'parcel_description' in data and data['parcel_description']:
            description = str(data['parcel_description']).strip()
            if len(description) > 1000:
                errors['parcel_description'] = 'Parcel description must be less than 1000 characters'
        
        if 'parcel_dimensions' in data and data['parcel_dimensions']:
            dimensions = str(data['parcel_dimensions']).strip()
            if not OrderValidator._validate_dimensions(dimensions):
                errors['parcel_dimensions'] = 'Dimensions format should be LxWxH (e.g., 30x20x15)'
        
        # 7. VALIDATE BOOLEAN FLAGS
        if 'fragile' in data:
            if not isinstance(data['fragile'], (bool, int)):
                errors['fragile'] = 'Fragile must be true or false'
        
        if 'insurance_required' in data:
            if not isinstance(data['insurance_required'], (bool, int)):
                errors['insurance_required'] = 'Insurance required must be true or false'
        
        if 'is_express' in data:
            if not isinstance(data['is_express'], (bool, int)):
                errors['is_express'] = 'Express delivery must be true or false'
        
        if 'is_weekend' in data:
            if not isinstance(data['is_weekend'], (bool, int)):
                errors['is_weekend'] = 'Weekend flag must be true or false'
        
        # If there are any errors, return False
        if errors:
            return (False, {}, errors)
        
        # 8. BUILD VALIDATED DATA
        validated_data = {
            'pickup_lat': pickup_lat,
            'pickup_lng': pickup_lng,
            'pickup_address': pickup_address,
            'pickup_phone': (data.get('pickup_phone') or '').strip() or None,
            'destination_lat': destination_lat,
            'destination_lng': destination_lng,
            'destination_address': destination_address,
            'destination_phone': (data.get('destination_phone') or '').strip() or None,
            'weight_kg': weight_kg,
            'parcel_description': (data.get('parcel_description') or '').strip() or None,
            'parcel_dimensions': (data.get('parcel_dimensions') or '').strip() or None,
            'fragile': bool(data.get('fragile', False)),
            'insurance_required': bool(data.get('insurance_required', False)),
            'is_express': bool(data.get('is_express', False)),
            'is_weekend': bool(data.get('is_weekend', False))
        }
        
        return (True, validated_data, {})
    
    @staticmethod
    def validate_update_destination(data: dict) -> tuple:
        """
        Validate destination update request data
        
        Args:
            data: Update destination request data
            
        Returns:
            tuple: (is_valid: bool, validated_data: dict, errors: dict)
        """
        errors = {}
        validated_data = {}
        
        # Required fields for destination update
        required_fields = {
            'destination_lat': 'Destination latitude is required',
            'destination_lng': 'Destination longitude is required',
            'destination_address': 'Destination address is required'
        }
        
        for field, error_msg in required_fields.items():
            if field not in data or data[field] is None:
                errors[field] = error_msg
        
        if errors:
            return (False, {}, errors)
        
        # Validate coordinates
        try:
            destination_lat = float(data['destination_lat'])
            destination_lng = float(data['destination_lng'])
        except (ValueError, TypeError):
            errors['coordinates'] = 'Coordinates must be valid numbers'
            return (False, {}, errors)
        
        if not (-90 <= destination_lat <= 90) or not (-180 <= destination_lng <= 180):
            errors['coordinates'] = 'Invalid coordinate ranges'
            return (False, {}, errors)
        
        # Validate address
        destination_address = (data.get('destination_address') or '').strip()
        if not destination_address or len(destination_address) < 3:
            errors['destination_address'] = 'Destination address must be at least 3 characters'
        elif len(destination_address) > 500:
            errors['destination_address'] = 'Destination address must be less than 500 characters'
        
        if errors:
            return (False, {}, errors)
        
        # Build validated data
        validated_data = {
            'destination_lat': destination_lat,
            'destination_lng': destination_lng,
            'destination_address': destination_address,
            'destination_phone': (data.get('destination_phone') or '').strip() or None
        }
        
        return (True, validated_data, {})
    
    @staticmethod
    def _validate_phone(phone: str) -> bool:
        """
        Validate phone number format
        Accepts Kenyan format and international format
        
        Args:
            phone: Phone number to validate
            
        Returns:
            bool: True if valid phone format
        """
        phone = str(phone).strip()
        
        # Pattern: optional +, followed by digits and optional spaces/dashes
        # Kenyan: 0712345678, +254712345678, +254-712-345678
        pattern = r'^\+?(\d[\d\s\-]{8,15}\d)$'
        
        return bool(re.match(pattern, phone))
    
    @staticmethod
    def _validate_dimensions(dimensions: str) -> bool:
        """
        Validate parcel dimensions format (LxWxH)
        
        Args:
            dimensions: Dimensions string (e.g., "30x20x15")
            
        Returns:
            bool: True if valid format
        """
        # Pattern: number x number x number
        pattern = r'^\d+\.?\d*\s*x\s*\d+\.?\d*\s*x\s*\d+\.?\d*$'
        
        return bool(re.match(pattern, dimensions, re.IGNORECASE))


__all__ = ['OrderValidator']
