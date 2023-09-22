"""Pulls SCAN metadata from LONI."""

import logging
import re
from io import BytesIO

import boto3
import pandas as pd
from flywheel import FileSpec, Project
from flywheel_adaptor.flywheel_proxy import FlywheelProxy

log = logging.getLogger(__name__)


def get_parameter(parameter_name) -> str:
    # Get parameter from SSM Parameter Store
    ssm_client = boto3.client('ssm', region_name='us-west-2')
    response = ssm_client.get_parameter(Name=parameter_name,
                                        WithDecryption=True)
    parameter_value = response['Parameter']['Value']
    return parameter_value


def get_fw_proxy() -> FlywheelProxy:
    api_key = get_parameter(parameter_name='/prod/flywheel/gearbot/apikey')
    fw = FlywheelProxy(api_key=api_key)
    return fw


def stream_file_to_container(fw_file: FileSpec, container: Project) -> None:
    container.upload_file(fw_file)


def upload_center_file(adcid, table_data: pd.DataFrame, table_name: str):
    print(f"Uploading {table_name} for adcid {adcid}")

    csv_data = table_data.to_csv(index=False)
    fw_file = FileSpec(f"{table_name}.csv", csv_data)

    fw = get_fw_proxy()

    group = fw.find_groups_by_tag(tag_pattern=f"adcid-{adcid}")
    project = fw.get_project(group=group[0], project_label="ingest-scan")

    stream_file_to_container(fw_file=fw_file, container=project)
    return


def split_table(table_data, table_name):
    """Splits the table data into center subsets and uploads them to a FW
    project."""

    if 'ADCID' in table_data.columns:
        # unique_adcid = list(table_data['ADCID'].unique())
        unique_adcid = [42]
        for adcid in unique_adcid:
            center_subset = table_data.loc[table_data['ADCID'] == adcid]

            # Upload center subset to FW
            upload_center_file(adcid, center_subset, table_name)
            exit()

    elif 'SITE' in table_data.columns:
        # unique_adcid = table_data['SITE'].unique()
        unique_adcid = ['Wake Forest University (ADC42)']
        for adcid in unique_adcid:
            adcid = re.search("([^(]+)\(ADC\s?(\d+)\)", adcid).group(2).strip()
            center_subset = table_data[table_data['SITE'].str.contains(
                f'\(ADC\s?{adcid}\)')]

            # Upload center subset to FW
            upload_center_file(adcid, center_subset, table_name)
            exit()

    else:
        log.error(
            f'{table_name} does not have a recognized column for the Center ID'
        )


def get_s3_client():
    # Get S3 credentials
    access_key = get_parameter(
        parameter_name='/prod/flywheel/gearbot/loni/accesskey')
    secret_key = get_parameter(
        parameter_name='/prod/flywheel/gearbot/loni/secretkey')
    region = 'us-west-2'

    # Initialize the S3 client
    client = boto3.client('s3',
                          aws_access_key_id=access_key,
                          aws_secret_access_key=secret_key,
                          region_name=region)

    return client


def download_table(s3_client, file_name) -> pd.DataFrame:
    bucket_name = 'loni-table-data'

    # Download the object from S3
    response = s3_client.get_object(Bucket=bucket_name, Key=file_name)
    object_data = response['Body'].read()

    # Convert the object data to a Pandas DataFrame
    data = pd.read_csv(BytesIO(object_data))

    return data


def run():
    """Pulls SCAN metadata from S3, splits the data by center, and uploads the
    data to the center-specific FW project.

    Args:
      flywheel_proxy: the proxy for the Flywheel instance
    """
    table_list = [
        "v_scan_upload_with_qc", "v_scan_mri_dashboard", "v_scan_pet_dashboard"
    ]

    s3_client = get_s3_client()
    try:
        for table_name in table_list:
            log.info(f"Downloading {table_name} from S3")
            table_data = download_table(s3_client,
                                        file_name=f"{table_name}.csv")

            log.info(f"Splitting table {table_name}")
            split_table(table_data, table_name)

    except Exception as e:
        log.error(f"{e}")
        print(e)


# if __name__ == '__main__':
#     run()
