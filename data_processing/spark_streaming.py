from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, expr
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType, TimestampType, MapType

# Define schema for crime data
crime_schema = StructType([
    # Common fields
    StructField("source", StringType(), True),
    StructField("timestamp", IntegerType(), True),
    
    # UK Police data fields
    StructField("category", StringType(), True),
    StructField("location_type", StringType(), True),
    StructField("location", MapType(StringType(), StringType()), True),
    StructField("context", StringType(), True),
    StructField("outcome_status", MapType(StringType(), StringType()), True),
    StructField("persistent_id", StringType(), True),
    StructField("id", StringType(), True),
    StructField("location_subtype", StringType(), True),
    StructField("month", StringType(), True),
    StructField("location_name", StringType(), True),
    
    # Chicago data fields
    StructField("case_number", StringType(), True),
    StructField("date", StringType(), True),
    StructField("block", StringType(), True),
    StructField("iucr", StringType(), True),
    StructField("primary_type", StringType(), True),
    StructField("description", StringType(), True),
    StructField("location_description", StringType(), True),
    StructField("arrest", StringType(), True),
    StructField("domestic", StringType(), True),
    StructField("beat", StringType(), True),
    StructField("district", StringType(), True),
    StructField("ward", StringType(), True),
    StructField("community_area", StringType(), True),
    StructField("fbi_code", StringType(), True),
    StructField("x_coordinate", StringType(), True),
    StructField("y_coordinate", StringType(), True),
    StructField("latitude", StringType(), True),
    StructField("longitude", StringType(), True),
    
    # NYC data fields
    StructField("cmplnt_num", StringType(), True),
    StructField("cmplnt_fr_dt", StringType(), True),
    StructField("cmplnt_fr_tm", StringType(), True),
    StructField("cmplnt_to_dt", StringType(), True),
    StructField("cmplnt_to_tm", StringType(), True),
    StructField("addr_pct_cd", StringType(), True),
    StructField("rpt_dt", StringType(), True),
    StructField("ky_cd", StringType(), True),
    StructField("ofns_desc", StringType(), True),
    StructField("pd_cd", StringType(), True),
    StructField("pd_desc", StringType(), True),
    StructField("crm_atpt_cptd_cd", StringType(), True),
    StructField("law_cat_cd", StringType(), True),
    StructField("boro_nm", StringType(), True),
    
    # LA data fields
    StructField("dr_no", StringType(), True),
    StructField("date_rptd", StringType(), True),
    StructField("date_occ", StringType(), True),
    StructField("time_occ", StringType(), True),
    StructField("area", StringType(), True),
    StructField("area_name", StringType(), True),
    StructField("rpt_dist_no", StringType(), True),
    StructField("crm_cd", StringType(), True),
    StructField("crm_cd_desc", StringType(), True),
    StructField("status", StringType(), True),
    StructField("status_desc", StringType(), True),
    StructField("weapon_used_cd", StringType(), True),
    StructField("weapon_desc", StringType(), True),
    StructField("mocodes", StringType(), True),
    StructField("vict_age", StringType(), True),
    StructField("vict_sex", StringType(), True),
    StructField("vict_descent", StringType(), True),
    StructField("premis_cd", StringType(), True),
    StructField("premis_desc", StringType(), True),
    StructField("cross_street", StringType(), True)
])

def create_spark_session():
    """Create a Spark session for structured streaming"""
    return (SparkSession.builder
            .appName("CrimeDataProcessing")
            .config("spark.sql.streaming.checkpointLocation", "/tmp/checkpoint")
            .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.2,io.delta:delta-core_2.12:1.0.0")
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
            .getOrCreate())

def process_crime_data():
    """Process crime data from Kafka and store in Delta Lake"""
    spark = create_spark_session()
    
    # Read from Kafka
    kafka_df = (spark.readStream
                .format("kafka")
                .option("kafka.bootstrap.servers", "localhost:9092")
                .option("subscribe", "crime-incidents")
                .option("startingOffsets", "latest")
                .load())
    
    # Parse JSON data
    parsed_df = kafka_df.select(
        from_json(col("value").cast("string"), crime_schema).alias("data")
    ).select("data.*")
    
    # Convert timestamp to timestamp type
    parsed_df = parsed_df.withColumn(
        "event_time", 
        expr("CAST(CAST(timestamp AS TIMESTAMP) AS TIMESTAMP)")
    )
    
    # Process by data source
    uk_df = parsed_df.filter(col("source") == "uk_police")
    chicago_df = parsed_df.filter(col("source") == "chicago")
    nyc_df = parsed_df.filter(col("source") == "nyc")
    la_df = parsed_df.filter(col("source") == "la")
    
    # Extract crime type across different sources
    uk_df = uk_df.withColumn("crime_type", col("category"))
    chicago_df = chicago_df.withColumn("crime_type", col("primary_type"))
    nyc_df = nyc_df.withColumn("crime_type", col("ofns_desc"))
    la_df = la_df.withColumn("crime_type", col("crm_cd_desc"))
    
    # Union all sources
    unified_df = uk_df.select("source", "timestamp", "event_time", "crime_type", "location_name")
    unified_df = unified_df.union(
        chicago_df.select("source", "timestamp", "event_time", "crime_type", 
                         expr("district as location_name"))
    )
    unified_df = unified_df.union(
        nyc_df.select("source", "timestamp", "event_time", "crime_type", 
                     expr("boro_nm as location_name"))
    )
    unified_df = unified_df.union(
        la_df.select("source", "timestamp", "event_time", "crime_type", 
                    expr("area_name as location_name"))
    )
    
    # Aggregate crime data over windows
    crime_agg_df = (unified_df
                   .withWatermark("event_time", "1 hour")
                   .groupBy(
                       window(col("event_time"), "1 hour"),
                       col("source"),
                       col("location_name"),
                       col("crime_type")
                   )
                   .count()
                   .withColumnRenamed("count", "incident_count"))
    
    # Write to Delta Lake
    # Store raw data by source
    uk_query = (uk_df.writeStream
               .format("delta")
               .outputMode("append")
               .option("checkpointLocation", "/tmp/checkpoint/uk")
               .start("/home/ubuntu/mlops-crimerate-project/data/delta/uk"))
    
    chicago_query = (chicago_df.writeStream
                    .format("delta")
                    .outputMode("append")
                    .option("checkpointLocation", "/tmp/checkpoint/chicago")
                    .start("/home/ubuntu/mlops-crimerate-project/data/delta/chicago"))
    
    nyc_query = (nyc_df.writeStream
                .format("delta")
                .outputMode("append")
                .option("checkpointLocation", "/tmp/checkpoint/nyc")
                .start("/home/ubuntu/mlops-crimerate-project/data/delta/nyc"))
    
    la_query = (la_df.writeStream
               .format("delta")
               .outputMode("append")
               .option("checkpointLocation", "/tmp/checkpoint/la")
               .start("/home/ubuntu/mlops-crimerate-project/data/delta/la"))
    
    # Store aggregated data
    agg_query = (crime_agg_df.writeStream
                .format("delta")
                .outputMode("append")
                .option("checkpointLocation", "/tmp/checkpoint/aggregated")
                .start("/home/ubuntu/mlops-crimerate-project/data/delta/aggregated"))
    
    # Wait for termination
    uk_query.awaitTermination()
    chicago_query.awaitTermination()
    nyc_query.awaitTermination()
    la_query.awaitTermination()
    agg_query.awaitTermination()

if __name__ == "__main__":
    process_crime_data()
