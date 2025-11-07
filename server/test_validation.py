#!/usr/bin/env python
"""
Test validation logic for phone and location
"""
import re

def test_phone_validation(phone):
    """Test phone validation logic"""
    print(f"\n=== Testing Phone: '{phone}' ===")
    
    if phone:
        # Remove common phone formatting characters
        phone_digits = re.sub(r'[^\d]', '', str(phone))
        print(f"  Digits only: '{phone_digits}'")
        print(f"  Length: {len(phone_digits)}")
        
        # Check if it's a valid phone (7-15 digits, not a year like "2023")
        # Also reject if it's exactly 4 digits (likely a year)
        if (len(phone_digits) < 7 or len(phone_digits) > 15 or 
            len(phone_digits) == 4 or  # Reject 4-digit numbers (years)
            phone_digits in ['2019', '2020', '2021', '2022', '2023', '2024', '2025', '2026', '2027', '2028', '2029', '2030']):
            print(f"  ❌ REJECTED: Invalid phone (appears to be a year)")
            return None
        else:
            print(f"  ✅ VALID")
            return phone
    return None


def test_location_validation(location, companies=[]):
    """Test location validation logic"""
    print(f"\n=== Testing Location: '{location}' ===")
    
    if location:
        location_lower = location.lower().strip()
        print(f"  Lowercase: '{location_lower}'")
        print(f"  Length: {len(location)}")
        print(f"  Is uppercase: {location.isupper()}")
        
        # Reject if it's one of the companies from work experience
        if location_lower in companies:
            print(f"  ❌ REJECTED: Company name")
            return None
        
        # Reject if it's too short (likely an acronym like "ROC", "AUC", "SQL")
        elif len(location) <= 3 and location.isupper():
            print(f"  ❌ REJECTED: Short uppercase acronym")
            return None
        
        # Reject common technical terms that might be mistaken for locations
        elif location_lower in ['roc', 'auc', 'sql', 'aws', 'gcp', 'api', 'sdk', 'ide', 'npm', 'eda', 'etl', 'kpi']:
            print(f"  ❌ REJECTED: Technical term")
            return None
        
        # Reject if it contains common technical keywords
        elif any(keyword in location_lower for keyword in ['validation', 'testing', 'model', 'data', 'analysis']):
            print(f"  ❌ REJECTED: Contains technical keyword")
            return None
        
        else:
            print(f"  ✅ VALID")
            return location
    
    return None


if __name__ == '__main__':
    print("=" * 60)
    print("PHONE VALIDATION TESTS")
    print("=" * 60)
    
    # Test valid phones
    test_phone_validation("555-123-4567")
    test_phone_validation("+1-555-123-4567")
    test_phone_validation("(555) 123-4567")
    
    # Test invalid phones (years)
    test_phone_validation("2020")
    test_phone_validation("2023")
    test_phone_validation("2024")
    test_phone_validation("2025")
    
    # Test edge cases
    test_phone_validation("123456")  # Too short
    test_phone_validation("12345678901234567")  # Too long
    
    print("\n" + "=" * 60)
    print("LOCATION VALIDATION TESTS")
    print("=" * 60)
    
    # Test valid locations
    test_location_validation("Houston, TX")
    test_location_validation("New York, NY")
    test_location_validation("Edmond, OK")
    test_location_validation("Hyderabad, India")
    
    # Test invalid locations (acronyms)
    test_location_validation("ROC")
    test_location_validation("AUC")
    test_location_validation("SQL")
    test_location_validation("AWS")
    
    # Test invalid locations (technical terms)
    test_location_validation("roc")
    test_location_validation("etl")
    test_location_validation("api")
    
    # Test invalid locations (contains keywords)
    test_location_validation("Data Analysis")
    test_location_validation("Model Testing")
    
    # Test company names
    companies = ['halliburton', 'vertocity', 'google']
    test_location_validation("Halliburton", companies)
    test_location_validation("VERTOCITY", companies)
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
