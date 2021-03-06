import sys
import os
from datetime import datetime
from pyspark import SparkConf, SparkContext
from pyspark.sql import SparkSession
from pyspark.sql.types import (StructType, StructField as Fld, DoubleType as Dbl,
                               IntegerType as Int, DateType as Date,
                               BooleanType as Boolean, FloatType as Float,
                               LongType as Long, StringType as String,
                               ArrayType as Array)
from pyspark.sql.functions import col


def create_spark_session(aws_key, aws_secret_key):
    """
    Description: Creates spark session.
    Returns:
        spark session object
    """

    spark = SparkSession \
        .builder \
        .config("spark.executor.heartbeatInterval", "40s") \
        .getOrCreate()
    
    spark.sparkContext._jsc.hadoopConfiguration().set("fs.s3a.impl",
                                                      "org.apache.hadoop.fs.s3a.S3AFileSystem")
    spark.sparkContext._jsc.hadoopConfiguration().set("fs.s3a.access.key", aws_key)
    spark.sparkContext._jsc.hadoopConfiguration().set("fs.s3a.secret.key", aws_secret_key)
    spark.sparkContext._jsc.hadoopConfiguration().set("fs.s3a.endpoint", "s3.amazonaws.com")
    spark.sparkContext._jsc.hadoopConfiguration().set("fs.s3a.connection.timeout", "100")
    spark.sparkContext._jsc.hadoopConfiguration().set("fs.s3a.connection.maximum", "5000")
    return spark


def format_datetime(ts):
    return datetime.fromtimestamp(ts/1000.0) 

if __name__ == "__main__":
    s3_bucket = sys.argv[1]
    s3_key = sys.argv[2]
    aws_key = sys.argv[3]
    aws_secret_key = sys.argv[4]
    redshift_conn_string = sys.argv[5]
    db_user = sys.argv[6]
    db_pass = sys.argv[7]

    spark = create_spark_session(aws_key, aws_secret_key)

    movies_schema = StructType([
        Fld("adult", String()),
        Fld("belongs_to_collection", Long()),
        Fld("budget", Long()),
        Fld("genres", String()),
        Fld("homepage", String()),
        Fld("id", Int()),
        Fld("imdb_id", String()),
        Fld("original_language", String()),
        Fld("original_title", String()),
        Fld("overview", String()),
        Fld("popularity", Dbl()),
        Fld("poster_path", String()),
        Fld("production_companies", String()),
        Fld("production_countries",  String()),
        Fld("release_date", Date()),
        Fld("revenue", Long()),
        Fld("runtime", Float()),
        Fld("spoken_languages", String()),
        Fld("status", String()),
        Fld("tagline", String()),
        Fld("title", String()),
        Fld("video", Boolean()),
        Fld("vote_average", Float()),
        Fld("vote_count", Int())
    ])


    movies_df = spark.read.option("header", "true") \
                           .csv("s3a://{}/{}/movies_metadata.csv".format(s3_bucket, s3_key), 
                                schema=movies_schema)


    movies_df = movies_df.select(
        col("id").alias("movie_id"),
        col("adult").alias("is_adult"),
        col("budget"),
        col("original_language"),
        col("title"),
        col("popularity"),
        col("release_date"),
        col("revenue"),
        col("vote_count"),
        col("vote_average")
    )

    movies_df = movies_df.na.drop()
    
    movies_df.write \
             .format("jdbc")  \
             .option("url", redshift_conn_string) \
             .option("dbtable", "movies.stage_movies") \
             .option("user", sys.argv[6]) \
             .option("password", sys.argv[7]) \
             .option("driver", "com.amazon.redshift.jdbc42.Driver") \
             .mode("append") \
             .save()