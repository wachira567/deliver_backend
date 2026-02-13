import googlemaps
import os
import math

class MapsService:
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        self.client = None
        if self.api_key:
            try:
                self.client = googlemaps.Client(key=self.api_key)
            except Exception as e:
                print(f"Warning: Failed to initialize Google Maps client: {e}")

    def calculate_distance(self, origin, destination):
        """
        Calculate distance and duration between two locations
        """
        # specific check for coordinates
        lat1, lon1 = None, None
        lat2, lon2 = None, None

        if isinstance(origin, tuple):
             lat1, lon1 = origin
        elif isinstance(origin, str) and ',' in origin:
             try:
                 lat1, lon1 = map(float, origin.split(','))
             except: pass
        
        if isinstance(destination, tuple):
             lat2, lon2 = destination
        elif isinstance(destination, str) and ',' in destination:
             try:
                 lat2, lon2 = map(float, destination.split(','))
             except: pass

        # Use Google Maps if available
        if self.client:
            try:
                # Convert tuples to string format if needed
                origin_str = origin
                if isinstance(origin, tuple):
                    origin_str = f"{origin[0]},{origin[1]}"
                
                dest_str = destination
                if isinstance(destination, tuple):
                    dest_str = f"{destination[0]},{destination[1]}"
                    
                result = self.client.distance_matrix(
                    origins=[origin_str],
                    destinations=[dest_str],
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
            except Exception as e:
                print(f"Google Maps API failed, falling back to Haversine: {e}")

        # Fallback to Haversine
        if lat1 is not None and lon1 is not None and lat2 is not None and lon2 is not None:
            return self.calculate_haversine(lat1, lon1, lat2, lon2)
            
        return {
            'distance_km': 0,
            'duration_minutes': 0,
            'status': 'error',
            'message': 'Could not calculate distance (Maps API missing and coordinates invalid)'
        }

    def calculate_haversine(self, lat1, lon1, lat2, lon2):
        try:
            R = 6371  # Earth radius in km
            dLat = math.radians(lat2 - lat1)
            dLon = math.radians(lon2 - lon1)
            a = math.sin(dLat/2) * math.sin(dLat/2) + \
                math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
                math.sin(dLon/2) * math.sin(dLon/2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            d = R * c
            
            # Estimate duration (assuming 40km/h average speed)
            duration_hours = d / 40
            duration_minutes = int(duration_hours * 60)
            
            return {
                'distance_km': round(d, 2),
                'duration_minutes': duration_minutes,
                'status': 'success',
                'method': 'haversine'
            }
        except Exception as e:
             return {
                'distance_km': 0,
                'duration_minutes': 0,
                'status': 'error',
                'message': str(e)
            }

if __name__ == '__main__':
    maps = MapsService()
    # Test with coordinates (Nairobi to Mombasa approx)
    print(maps.calculate_distance((-1.2921, 36.8219), (-4.0435, 39.6682)))