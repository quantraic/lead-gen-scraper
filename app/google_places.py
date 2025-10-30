import os
import requests
from datetime import datetime
import math

class PlacesSearcher:
    def __init__(self, api_key):
        self.api_key = api_key
        self.results = []
        self.base_url = "https://places.googleapis.com/v1/places:searchNearby"
        self.geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
    
    def calculate_grid_points(self, center_lat, center_lng, radius_miles, grid_spacing_miles=10):
        """
        Calculate grid points to cover the search area.
        """
        lat_per_mile = 1 / 69.0
        lng_per_mile = 1 / (69.0 * math.cos(math.radians(center_lat)))
        
        grid_points = []
        num_points = max(1, int(radius_miles / grid_spacing_miles))
        
        for i in range(-num_points, num_points + 1):
            for j in range(-num_points, num_points + 1):
                lat_offset = i * grid_spacing_miles * lat_per_mile
                lng_offset = j * grid_spacing_miles * lng_per_mile
                
                new_lat = center_lat + lat_offset
                new_lng = center_lng + lng_offset
                
                distance = self.haversine_distance(
                    center_lat, center_lng, new_lat, new_lng
                )
                
                if distance <= radius_miles:
                    grid_points.append((new_lat, new_lng))
        
        return grid_points
    
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points in miles"""
        R = 3959  # Earth's radius in miles
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def geocode_zipcode(self, zipcode):
        """Convert zipcode to lat/lng coordinates using Geocoding API"""
        try:
            params = {
                'address': zipcode,
                'key': self.api_key
            }
            response = requests.get(self.geocode_url, params=params)
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                location = data['results'][0]['geometry']['location']
                return location['lat'], location['lng']
            else:
                print(f"Geocoding error: {data.get('status')}")
                return None, None
        except Exception as e:
            print(f"Error geocoding zipcode: {e}")
            return None, None
    
    def search_nearby(self, keyword, lat, lng, radius_meters=16000):
        """
        Search for places near a location using NEW Places API
        """
        try:
            headers = {
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': self.api_key,
                'X-Goog-FieldMask': 'places.id,places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri,places.location,places.addressComponents'
            }
            
            body = {
                "includedTypes": ["veterinary_care"],
                "maxResultCount": 20,
                "locationRestriction": {
                    "circle": {
                        "center": {
                            "latitude": lat,
                            "longitude": lng
                        },
                        "radius": radius_meters
                    }
                }
            }
            
            # If keyword is not "veterinary clinic", use text search instead
            if keyword.lower() != "veterinary clinic":
                body = {
                    "textQuery": keyword,
                    "maxResultCount": 20,
                    "locationBias": {
                        "circle": {
                            "center": {
                                "latitude": lat,
                                "longitude": lng
                            },
                            "radius": radius_meters
                        }
                    }
                }
                # Use searchText endpoint instead
                search_url = "https://places.googleapis.com/v1/places:searchText"
                response = requests.post(search_url, headers=headers, json=body)
            else:
                response = requests.post(self.base_url, headers=headers, json=body)
            
            data = response.json()
            
            if 'places' in data:
                return data['places']
            else:
                print(f"API Response: {data}")
                return []
                
        except Exception as e:
            print(f"Error searching places: {e}")
            return []
    
    def parse_address_components(self, address_components):
        """Extract city, state, zip from address components"""
        city = ''
        state = ''
        zipcode = ''
        
        if not address_components:
            return city, state, zipcode
        
        for component in address_components:
            types = component.get('types', [])
            
            if 'locality' in types:
                city = component.get('longText', '')
            elif 'administrative_area_level_1' in types:
                state = component.get('shortText', '')
            elif 'postal_code' in types:
                zipcode = component.get('longText', '')
        
        return city, state, zipcode
    
    def search_area(self, keyword, zipcode, radius_miles):
        """
        Main search function that covers the entire area
        Returns list of unique places with details
        """
        print(f"Starting search for '{keyword}' within {radius_miles} miles of {zipcode}")
        
        # Get center coordinates
        center_lat, center_lng = self.geocode_zipcode(zipcode)
        if not center_lat:
            print("Could not geocode zipcode")
            return []
        
        print(f"Center coordinates: {center_lat}, {center_lng}")
        
        # Calculate grid points for comprehensive coverage
        grid_points = self.calculate_grid_points(center_lat, center_lng, radius_miles)
        print(f"Searching {len(grid_points)} grid points...")
        
        # Track unique places by place_id
        unique_places = {}
        
        # Search each grid point
        for idx, (lat, lng) in enumerate(grid_points, 1):
            print(f"Searching grid point {idx}/{len(grid_points)}...")
            
            places = self.search_nearby(keyword, lat, lng, radius_meters=16000)
            
            for place in places:
                place_id = place.get('id')
                
                if place_id in unique_places:
                    continue
                
                # Check if place is within target radius
                place_lat = place.get('location', {}).get('latitude')
                place_lng = place.get('location', {}).get('longitude')
                
                if not place_lat or not place_lng:
                    continue
                
                distance = self.haversine_distance(
                    center_lat, center_lng, place_lat, place_lng
                )
                
                if distance <= radius_miles:
                    # Parse address
                    address_components = place.get('addressComponents', [])
                    city, state, zipcode_parsed = self.parse_address_components(address_components)
                    
                    # Build lead data
                    lead_data = {
                        'name': place.get('displayName', {}).get('text', ''),
                        'address': place.get('formattedAddress', ''),
                        'city': city,
                        'state': state,
                        'zip': zipcode_parsed,
                        'phone': place.get('nationalPhoneNumber', ''),
                        'website': place.get('websiteUri', ''),
                        'place_id': place_id,
                        'email': '',
                        'facebook': '',
                        'instagram': '',
                        'linkedin': '',
                        'twitter': ''
                    }
                    
                    unique_places[place_id] = lead_data
        
        print(f"Found {len(unique_places)} unique places")
        return list(unique_places.values())
    
    def estimate_cost(self, radius_miles):
        """
        Estimate API cost for a search.
        New Places API pricing is different
        """
        grid_spacing = 10
        num_points = max(1, int(radius_miles / grid_spacing)) * 2 + 1
        num_searches = num_points ** 2
        
        estimated_places = num_searches * 10
        
        # New API: Nearby Search costs $0.032 per request
        search_cost = num_searches * 0.032
        
        total_cost = search_cost
        
        return {
            'estimated_searches': num_searches,
            'estimated_places': estimated_places,
            'nearby_cost': search_cost,
            'details_cost': 0,  # Details are included in search with new API
            'total_cost': total_cost
        }