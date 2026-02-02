"""
Google Maps Distance Calculation Service
Calculates distance between pickup and destination
"""
import googlemaps
import os

class MapsService:
    def __init__(self):
        api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY not found in environment variables")
        self.client = googlemaps.Client(key=api_key)
    
    def calculate_distance(self, origin, destination):
        """
        Calculate distance and duration between two locations
        
        Args:
            origin (str): Starting address or coordinates
            destination (str): Ending address or coordinates
            
        Returns:
            dict: {
                'distance_km': float,
                'duration_minutes': int,
                'status': str
            }
        """
        try:
            result = self.client.distance_matrix(
                origins=[origin],
                destinations=[destination],
                mode="driving"
            )
            
            if result['rows'][0]['elements'][0]['status'] == 'OK':
                distance_meters = result['rows'][0]['elements'][0]['distance']['value']
                duration_seconds = result['rows'][0]['elements'][0]['duration']['value']
                
                return {
                    'distance_km': round(distance_meters / 1000, 2),
                    'duration_minutes': round(duration_seconds / 60),
                    'status': 'success'
                }
            else:
                return {
                    'distance_km': 0,
                    'duration_minutes': 0,
                    'status': 'error',
                    'message': 'Could not calculate distance'
                }
        except Exception as e:
            return {
                'distance_km': 0,
                'duration_minutes': 0,
                'status': 'error',
                'message': str(e)
            }

# Example usage (for testing):
if __name__ == '__main__':
    maps = MapsService()
    result = maps.calculate_distance(
        "Nairobi, Kenya",
        "Mombasa, Kenya"
    )
    print(result)