import os
import json
import time
import requests
from kafka import KafkaProducer
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = "crime-incidents"

class CrimeDataProducer:
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
    def get_uk_police_data(self):
        """Get crime data from UK Police Data API"""
        # Get the previous month (API limitation)
        today = datetime.now()
        first_day_of_month = datetime(today.year, today.month, 1)
        last_month = first_day_of_month - timedelta(days=1)
        year_month = last_month.strftime("%Y-%m")
        
        # Define locations to query (major UK cities)
        locations = [
            {"lat": 51.5074, "lng": -0.1278},  # London
            {"lat": 52.4862, "lng": -1.8904},  # Birmingham
            {"lat": 53.4808, "lng": -2.2426},  # Manchester
            {"lat": 55.9533, "lng": -3.1883},  # Edinburgh
            {"lat": 53.8008, "lng": -1.5491}   # Leeds
        ]
        
        all_crimes = []
        
        for location in locations:
            url = f"https://data.police.uk/api/crimes-at-location?lat={location['lat']}&lng={location['lng']}&date={year_month}"
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    crimes = response.json()
                    for crime in crimes:
                        crime['source'] = 'uk_police'
                        crime['timestamp'] = int(time.time())
                        crime['location_name'] = self.get_location_name(location)
                        all_crimes.append(crime)
                    print(f"Retrieved {len(crimes)} crimes from UK Police API for {self.get_location_name(location)}")
            except Exception as e:
                print(f"Error retrieving UK Police data: {e}")
        
        return all_crimes
    
    def get_chicago_data(self):
        """Get crime data from Chicago Data Portal"""
        # Get data for the last 7 days
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
        
        url = f"https://data.cityofchicago.org/resource/ijzp-q8t2.json?$where=date > '{seven_days_ago}'&$limit=1000"
        
        try:
            response = requests.get(url)
            if response.status_code == 200:
                crimes = response.json()
                for crime in crimes:
                    crime['source'] = 'chicago'
                    crime['timestamp'] = int(time.time())
                print(f"Retrieved {len(crimes)} crimes from Chicago Data Portal")
                return crimes
            else:
                print(f"Error retrieving Chicago data: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error retrieving Chicago data: {e}")
            return []
    
    def get_nyc_data(self):
        """Get crime data from NYC Open Data"""
        # Get data for the last 7 days
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
        
        url = f"https://data.cityofnewyork.us/resource/5uac-w243.json?$where=cmplnt_fr_dt > '{seven_days_ago}'&$limit=1000"
        
        try:
            response = requests.get(url)
            if response.status_code == 200:
                crimes = response.json()
                for crime in crimes:
                    crime['source'] = 'nyc'
                    crime['timestamp'] = int(time.time())
                print(f"Retrieved {len(crimes)} crimes from NYC Open Data")
                return crimes
            else:
                print(f"Error retrieving NYC data: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error retrieving NYC data: {e}")
            return []
    
    def get_la_data(self):
        """Get crime data from Los Angeles Open Data"""
        # Get data for the last 7 days
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
        
        url = f"https://data.lacity.org/resource/2nrs-mtv8.json?$where=date_rptd > '{seven_days_ago}'&$limit=1000"
        
        try:
            response = requests.get(url)
            if response.status_code == 200:
                crimes = response.json()
                for crime in crimes:
                    crime['source'] = 'la'
                    crime['timestamp'] = int(time.time())
                print(f"Retrieved {len(crimes)} crimes from LA Open Data")
                return crimes
            else:
                print(f"Error retrieving LA data: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error retrieving LA data: {e}")
            return []
    
    def get_location_name(self, location):
        """Get location name based on coordinates"""
        if location["lat"] == 51.5074 and location["lng"] == -0.1278:
            return "London"
        elif location["lat"] == 52.4862 and location["lng"] == -1.8904:
            return "Birmingham"
        elif location["lat"] == 53.4808 and location["lng"] == -2.2426:
            return "Manchester"
        elif location["lat"] == 55.9533 and location["lng"] == -3.1883:
            return "Edinburgh"
        elif location["lat"] == 53.8008 and location["lng"] == -1.5491:
            return "Leeds"
        else:
            return "Unknown"
    
    def produce_data(self):
        """Produce crime data to Kafka topic"""
        # Get UK Police data
        uk_crimes = self.get_uk_police_data()
        for crime in uk_crimes:
            self.producer.send(KAFKA_TOPIC, crime)
        
        # Get Chicago data
        chicago_crimes = self.get_chicago_data()
        for crime in chicago_crimes:
            self.producer.send(KAFKA_TOPIC, crime)
        
        # Get NYC data
        nyc_crimes = self.get_nyc_data()
        for crime in nyc_crimes:
            self.producer.send(KAFKA_TOPIC, crime)
        
        # Get LA data
        la_crimes = self.get_la_data()
        for crime in la_crimes:
            self.producer.send(KAFKA_TOPIC, crime)
        
        # Flush to ensure all messages are sent
        self.producer.flush()
        
        total_crimes = len(uk_crimes) + len(chicago_crimes) + len(nyc_crimes) + len(la_crimes)
        print(f"Produced {total_crimes} crime incidents to Kafka")
    
    def run(self, interval=3600):
        """Run the producer continuously with a specified interval (default: 1 hour)"""
        try:
            while True:
                print(f"Fetching crime data at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                self.produce_data()
                print(f"Waiting {interval} seconds until next fetch...")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("Producer stopped by user")
        finally:
            self.producer.close()

if __name__ == "__main__":
    producer = CrimeDataProducer()
    producer.run()
