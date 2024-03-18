import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from datetime import datetime, timedelta
from facebook_business.api import FacebookAdsApi

# Initialize the SparkSession
spark = SparkSession.builder \
    .appName("FacebookAdsAnalysis") \
    .getOrCreate()

# Initialize the FacebookAdsApi
my_app_id = ''
my_app_secret = ''
my_access_token = ''
FacebookAdsApi.init(my_app_id, my_app_secret, my_access_token)

# Specify the fields to fetch for insights
insights_fields = [
    'account_id',
    'account_name',
    'campaign_id',
    'adset_id',
    'ad_id',
    'account_currency',
    'reach',
    'impressions',
    'clicks',
    'cpc',
    'spend',
    'date_start',
    'date_stop'
]

# Specify the fields to fetch for campaigns
campaign_fields = [
    'id',
    'name',
    'status',
    'effective_status',
    'objective',
    'start_time',
    'stop_time'
]

# Specify the params for the last 6 months
six_months_ago = datetime.now() - timedelta(days=365)
params = {
    'level': 'campaign',
    'time_range': {'since': six_months_ago.strftime('%Y-%m-%d'), 'until': datetime.now().strftime('%Y-%m-%d')},
    'time_increment': 1,  # Fetch day-wise data
}

# Retry mechanism for HTTP requests
def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# Fetch the insights data with retry mechanism
def fetch_insights():
    try:
        with requests_retry_session() as session:
            ad_account = AdAccount('act_701970735050548')
            return ad_account.get_insights(fields=insights_fields, params=params)
    except Exception as e:
        print("Error fetching insights:", e)
        return None

# Fetch the campaign data with retry mechanism
def fetch_campaigns():
    try:
        with requests_retry_session() as session:
            ad_account = AdAccount('act_701970735050548')
            return ad_account.get_campaigns(fields=campaign_fields)
    except Exception as e:
        print("Error fetching campaigns:", e)
        return None

# Fetch the insights data
insights = fetch_insights()

# Fetch the campaign data
campaigns = fetch_campaigns()

# Check if data is fetched successfully
if insights is not None and campaigns is not None:
    # Convert insights data to a DataFrame
    insights_rdd = spark.sparkContext.parallelize(insights)
    insights_df = insights_rdd.toDF()

    # Convert campaign data to a DataFrame
    campaigns_rdd = spark.sparkContext.parallelize(campaigns)
    campaigns_df = campaigns_rdd.toDF()

    # Save insights data to CSV
    insights_df.write.csv('Hadoop/Bronze/insights.csv', mode='overwrite', header=True)

    # Save campaign data to CSV
    campaigns_df.write.csv('Hadoop/Bronze/campaigns.csv', mode='overwrite', header=True)

    print("Data saved to 'Hadoop/Bronze/insights.csv' and 'Hadoop/Bronze/campaigns.csv'")
else:
    print("Failed to fetch data.")
