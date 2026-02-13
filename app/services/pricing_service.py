"""
Pricing Service for Order Calculation
Handles price breakdowns, weight categories, and delivery time estimates
"""
from decimal import Decimal
from enum import Enum as PyEnum


class WeightCategory(PyEnum):
    """Weight categories for pricing"""
    SMALL = 'SMALL'       # < 5kg
    MEDIUM = 'MEDIUM'     # 5-20kg
    LARGE = 'LARGE'       # 20-50kg
    XLARGE = 'XLARGE'     # > 50kg


class PricingService:
    """Service for calculating delivery prices and estimates"""
    
    # Pricing constants (in KES)
    BASE_PRICE = 0  # Base fare
    DISTANCE_RATE = 1  # Per km (Demo rate)
    
    # Weight category pricing
    WEIGHT_PRICES = {
        WeightCategory.SMALL.value: 0,      # 0-5kg
        WeightCategory.MEDIUM.value: 0,     # 5-20kg
        WeightCategory.LARGE.value: 0,      # 20-50kg
        WeightCategory.XLARGE.value: 0,    # > 50kg
    }
    
    # Extra charge percentages
    FRAGILE_CHARGE_PERCENT = 0.15  # 15% extra for fragile items
    INSURANCE_CHARGE_PERCENT = 0.10  # 10% extra for insurance
    EXPRESS_CHARGE_PERCENT = 0.25  # 25% extra for express delivery
    WEEKEND_CHARGE_PERCENT = 0.20  # 20% extra for weekend delivery
    
    # Delivery speed estimates (km/hour)
    NORMAL_SPEED_KMH = 40
    EXPRESS_SPEED_KMH = 60
    
    @staticmethod
    def determine_weight_category(weight_kg: float) -> str:
        """
        Determine weight category based on weight in kg
        
        Args:
            weight_kg: Weight in kilograms
            
        Returns:
            str: Weight category ('SMALL', 'MEDIUM', 'LARGE', 'XLARGE')
        """
        weight = float(weight_kg)
        
        if weight < 5:
            return WeightCategory.SMALL.value
        elif weight < 20:
            return WeightCategory.MEDIUM.value
        elif weight < 50:
            return WeightCategory.LARGE.value
        else:
            return WeightCategory.XLARGE.value
    
    @staticmethod
    def calculate_price_breakdown(distance_km: float, weight_kg: float, 
                                 is_fragile: bool = False, needs_insurance: bool = False,
                                 is_express: bool = False, is_weekend: bool = False) -> dict:
        """
        Calculate detailed price breakdown for an order
        
        Args:
            distance_km: Distance in kilometers
            weight_kg: Weight in kilograms
            is_fragile: Whether item is fragile
            needs_insurance: Whether insurance is needed
            is_express: Whether express delivery is requested
            is_weekend: Whether delivery is on weekend
            
        Returns:
            dict: {
                'base_price': float,
                'distance_price': float,
                'weight_price': float,
                'extra_charges': {
                    'fragile': float,
                    'insurance': float,
                    'express': float,
                    'weekend': float,
                    'total': float
                },
                'total_price': float,
                'currency': 'KES'
            }
        """
        # Calculate base components
        base_price = PricingService.BASE_PRICE
        distance_price = float(distance_km) * PricingService.DISTANCE_RATE
        
        # Determine weight category and price
        weight_category = PricingService.determine_weight_category(weight_kg)
        weight_price = PricingService.WEIGHT_PRICES.get(weight_category, 150)
        
        # Subtotal before extras
        subtotal = base_price + distance_price + weight_price
        
        # Calculate extra charges
        extra_charges = {}
        fragile_charge = 0
        insurance_charge = 0
        express_charge = 0
        weekend_charge = 0
        
        if is_fragile:
            fragile_charge = subtotal * PricingService.FRAGILE_CHARGE_PERCENT
            extra_charges['fragile'] = round(fragile_charge, 2)
        else:
            extra_charges['fragile'] = 0
        
        if needs_insurance:
            insurance_charge = subtotal * PricingService.INSURANCE_CHARGE_PERCENT
            extra_charges['insurance'] = round(insurance_charge, 2)
        else:
            extra_charges['insurance'] = 0
        
        if is_express:
            express_charge = subtotal * PricingService.EXPRESS_CHARGE_PERCENT
            extra_charges['express'] = round(express_charge, 2)
        else:
            extra_charges['express'] = 0
        
        if is_weekend:
            weekend_charge = subtotal * PricingService.WEEKEND_CHARGE_PERCENT
            extra_charges['weekend'] = round(weekend_charge, 2)
        else:
            extra_charges['weekend'] = 0
        
        total_extra = fragile_charge + insurance_charge + express_charge + weekend_charge
        extra_charges['total'] = round(total_extra, 2)
        
        # Calculate final total
        total_price = subtotal + total_extra
        
        return {
            'base_price': round(base_price, 2),
            'distance_price': round(distance_price, 2),
            'weight_price': round(weight_price, 2),
            'extra_charges': extra_charges,
            'total_price': round(total_price, 2),
            'currency': 'KES'
        }
    
    @staticmethod
    def calculate_estimated_delivery_time(distance_km: float, is_express: bool = False) -> int:
        """
        Calculate estimated delivery time in minutes
        
        Args:
            distance_km: Distance in kilometers
            is_express: Whether express delivery is requested
            
        Returns:
            int: Estimated delivery time in minutes
        """
        # Select speed based on delivery type
        speed_kmh = PricingService.EXPRESS_SPEED_KMH if is_express else PricingService.NORMAL_SPEED_KMH
        
        # Calculate travel time
        travel_hours = float(distance_km) / speed_kmh
        travel_minutes = travel_hours * 60
        
        # Add buffer time for pickup and handoff (15 minutes)
        buffer_minutes = 15
        
        total_minutes = int(travel_minutes + buffer_minutes)
        
        # Ensure minimum 30 minutes and maximum 480 minutes (8 hours)
        return max(30, min(total_minutes, 480))
    
    @staticmethod
    def create_order_summary(validated_data: dict) -> dict:
        """
        Create a complete order summary with pricing and timing
        
        Args:
            validated_data: Validated order data with:
                - pickup_lat, pickup_lng, pickup_address
                - destination_lat, destination_lng, destination_address
                - weight_kg
                - fragile, insurance_required, is_express, is_weekend (optional)
                
        Returns:
            dict: {
                'distance': {
                    'km': float,
                    'origin_address': str,
                    'destination_address': str
                },
                'estimated_delivery': {
                    'minutes': int,
                    'express': bool
                },
                'price_breakdown': {pricing details},
                'weight_category': str
            }
        """
        from app.services.maps_service import MapsService
        
        # Get distance from Maps API
        maps_service = MapsService()
        origin = (validated_data['pickup_lat'], validated_data['pickup_lng'])
        destination = (validated_data['destination_lat'], validated_data['destination_lng'])
        
        distance_result = maps_service.calculate_distance(origin, destination)
        
        distance_km = distance_result['distance_km']
        
        # Determine weight category
        weight_category = PricingService.determine_weight_category(validated_data['weight_kg'])
        
        # Calculate price breakdown
        price_breakdown = PricingService.calculate_price_breakdown(
            distance_km=distance_km,
            weight_kg=validated_data['weight_kg'],
            is_fragile=validated_data.get('fragile', False),
            needs_insurance=validated_data.get('insurance_required', False),
            is_express=validated_data.get('is_express', False),
            is_weekend=validated_data.get('is_weekend', False)
        )
        
        # Estimate delivery time
        estimated_minutes = PricingService.calculate_estimated_delivery_time(
            distance_km,
            is_express=validated_data.get('is_express', False)
        )
        
        return {
            'distance': {
                'km': distance_km,
                'origin_address': validated_data.get('pickup_address', ''),
                'destination_address': validated_data.get('destination_address', '')
            },
            'estimated_delivery': {
                'minutes': estimated_minutes,
                'express': validated_data.get('is_express', False)
            },
            'price_breakdown': price_breakdown,
            'weight_category': weight_category
        }


# For backwards compatibility with models
__all__ = ['PricingService', 'WeightCategory']
